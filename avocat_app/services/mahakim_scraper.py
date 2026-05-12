# avocat_app/services/mahakim_scraper.py
"""
Service Selenium pour synchroniser les données d'affaires depuis mahakim.ma.

Le site mahakim.ma est une Angular SPA avec des composants PrimeNG.
Formulaire de suivi: https://www.mahakim.ma/#/suivi/dossier-suivi

Structure du formulaire:
  - input[formcontrolname="numero"]   → رقم الملف
  - input[formcontrolname="mark"]     → رمز الملف (maxlength=4)
  - input[formcontrolname="annee"]    → السنة (maxlength=4)
  - p-dropdown[formcontrolname="tribunal"]              → محاكم الاستئناف
  - p-checkbox[formcontrolname="si_tribunaux_primaires"] → تفعيل المحاكم الابتدائية
  - p-dropdown[formcontrolname="tribunaux_primaires"]    → المحاكم الابتدائية (visible après checkbox)
  - button.btn-add[type="submit"]     → بحث

Les deux dropdowns utilisent optionvalue="idJuridiction" et optionlabel="nomJuridiction".
Le dropdown tribunaux_primaires dépend du tribunal d'appel sélectionné.

Stratégie d'extraction:
  On utilise Chrome DevTools Protocol (CDP) pour intercepter les réponses HTTP
  de l'API Angular. Cela donne les vrais idJuridiction/nomJuridiction sans
  dépendre du rendu DOM de PrimeNG.
"""
import json as _json
import logging
import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
)

logger = logging.getLogger(__name__)

MAHAKIM_URL = "https://www.mahakim.ma/#/suivi/dossier-suivi"


class MahakimScraper:
    """Scraping du portail mahakim.ma (Angular/PrimeNG)."""

    def __init__(self, headless=True, timeout=30):
        self.headless = headless
        self.timeout = timeout
        self.driver = None

    def _create_driver(self):
        opts = Options()
        if self.headless:
            opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--lang=ar")
        # Activer les logs réseau (CDP) pour intercepter les réponses API
        opts.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        try:
            self.driver = webdriver.Chrome(options=opts)
            self.driver.set_page_load_timeout(self.timeout)
        except WebDriverException as e:
            logger.error("Impossible de lancer Chrome/Chromium: %s", e)
            raise

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None

    def __enter__(self):
        self._create_driver()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------
    # Interception réseau via Chrome DevTools Protocol
    # ------------------------------------------------------------------

    def _flush_perf_logs(self):
        """Vide les logs performance (pour ne pas relire d'anciens résultats)."""
        try:
            self.driver.get_log('performance')
        except Exception:
            pass

    def _extract_tribunal_data_from_network(self):
        """
        Lit les logs performance CDP pour trouver les réponses HTTP
        contenant des listes de juridictions [{idJuridiction, nomJuridiction}].

        Returns:
            list of lists: chaque sous-liste = [{id: str, name: str}, ...]
        """
        all_results = []
        try:
            logs = self.driver.get_log('performance')
            for entry in logs:
                try:
                    msg = _json.loads(entry['message'])['message']
                    if msg['method'] != 'Network.responseReceived':
                        continue
                    params = msg['params']
                    request_id = params['requestId']
                    resp = params.get('response', {})
                    url = resp.get('url', '')
                    mime = resp.get('mimeType', '')

                    # Ne garder que les réponses JSON
                    if 'json' not in mime and 'javascript' not in mime:
                        continue

                    try:
                        body_resp = self.driver.execute_cdp_cmd(
                            'Network.getResponseBody', {'requestId': request_id}
                        )
                        data = _json.loads(body_resp.get('body', ''))
                    except Exception:
                        continue

                    # Chercher un tableau d'objets avec idJuridiction
                    if isinstance(data, list) and len(data) > 0:
                        first = data[0]
                        if isinstance(first, dict) and 'idJuridiction' in first:
                            options = [
                                {
                                    "id": str(item['idJuridiction']),
                                    "name": str(item.get('nomJuridiction', ''))
                                }
                                for item in data
                                if item.get('nomJuridiction')
                            ]
                            if options:
                                logger.info(
                                    "CDP: trouvé %d juridictions dans %s",
                                    len(options), url
                                )
                                all_results.append(options)
                except Exception:
                    continue
        except Exception as e:
            logger.warning("Erreur lecture logs performance: %s", e)

        return all_results

    # ------------------------------------------------------------------
    # Helpers — interaction avec PrimeNG
    # ------------------------------------------------------------------

    def _wait_for_angular(self):
        """Attend que l'app Angular soit chargée."""
        wait = WebDriverWait(self.driver, self.timeout)
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, 'input[formcontrolname="numero"]')
        ))
        time.sleep(1)

    def _fill_input(self, formcontrolname, value):
        """Remplit un champ input Angular."""
        el = self.driver.find_element(
            By.CSS_SELECTOR, f'input[formcontrolname="{formcontrolname}"]'
        )
        el.clear()
        el.send_keys(value)
        return el

    def _js_click(self, css_selector):
        """Clic via JavaScript (contourne les problèmes d'event Angular)."""
        self.driver.execute_script(
            "var el = document.querySelector(arguments[0]); if(el) el.click();",
            css_selector
        )

    def _extract_dropdown_options(self, formcontrolname):
        """
        Extrait les options d'un p-dropdown PrimeNG.
        Stratégie multi-niveaux:
          1. Intercepter les réponses HTTP (CDP) → vrais IDs
          2. ng.getComponent (dev mode)
          3. Scan récursif des propriétés internes Angular (__ngContext__)
          4. Clic JS + async polling des <li> rendus
        """
        selector = f'p-dropdown[formcontrolname="{formcontrolname}"]'

        # Vérifier que le dropdown existe
        dds = self.driver.find_elements(By.CSS_SELECTOR, selector)
        if not dds:
            logger.warning("Dropdown %s non trouvé", formcontrolname)
            return []

        # --- Méthode 1: Données réseau CDP (déjà capturées) ---
        network_data = self._extract_tribunal_data_from_network()
        if network_data:
            # Prendre le dernier résultat (le plus récent)
            return network_data[-1]

        # --- Méthode 2: ng.getComponent (dev mode uniquement) ---
        try:
            options = self.driver.execute_script("""
                var dd = document.querySelector(arguments[0]);
                if (!dd) return null;
                try {
                    var comp = ng.getComponent(dd);
                    if (comp && comp.options && comp.options.length > 0) {
                        return comp.options.map(function(o) {
                            return {
                                id: String(o.idJuridiction !== undefined ? o.idJuridiction : ''),
                                name: String(o.nomJuridiction || '')
                            };
                        }).filter(function(o) { return o.name; });
                    }
                } catch(e) {}
                return null;
            """, selector)
            if options:
                logger.info("ng.getComponent réussi pour %s: %d options", formcontrolname, len(options))
                return options
        except Exception:
            pass

        # --- Méthode 3: Scan profond des propriétés internes Angular ---
        try:
            options = self.driver.execute_script("""
                var dd = document.querySelector(arguments[0]);
                if (!dd) return null;

                // Chercher dans toutes les propriétés __ du DOM element
                var keys = Object.getOwnPropertyNames(dd);
                for (var k = 0; k < keys.length; k++) {
                    var key = keys[k];
                    if (!key.startsWith('__')) continue;
                    try {
                        var val = dd[key];
                        // val peut être un LView (tableau) ou un nombre
                        if (Array.isArray(val)) {
                            for (var i = 0; i < Math.min(val.length, 200); i++) {
                                var item = val[i];
                                if (!item || typeof item !== 'object') continue;

                                // Chercher .options directement
                                if (Array.isArray(item.options) && item.options.length > 0
                                    && item.options[0] && item.options[0].idJuridiction !== undefined) {
                                    return item.options.map(function(o) {
                                        return {id: String(o.idJuridiction), name: String(o.nomJuridiction || '')};
                                    }).filter(function(o) { return o.name; });
                                }

                                // Chercher dans les sous-propriétés (1 niveau)
                                var subKeys = Object.keys(item);
                                for (var s = 0; s < subKeys.length; s++) {
                                    try {
                                        var sub = item[subKeys[s]];
                                        if (Array.isArray(sub) && sub.length > 0
                                            && sub[0] && sub[0].idJuridiction !== undefined) {
                                            return sub.map(function(o) {
                                                return {id: String(o.idJuridiction), name: String(o.nomJuridiction || '')};
                                            }).filter(function(o) { return o.name; });
                                        }
                                    } catch(e2) {}
                                }
                            }
                        }
                    } catch(e) {}
                }
                return null;
            """, selector)
            if options:
                logger.info("Scan __ réussi pour %s: %d options", formcontrolname, len(options))
                return options
        except Exception:
            pass

        # --- Méthode 4: Clic JS + polling async des items rendus ---
        return self._extract_dropdown_options_click_js(formcontrolname)

    def _extract_dropdown_options_click_js(self, formcontrolname):
        """
        Ouvre le dropdown entièrement via JS, poll les items rendus,
        puis referme. Tout se passe côté JavaScript pour garantir
        que les événements Angular sont bien déclenchés.
        """
        selector = f'p-dropdown[formcontrolname="{formcontrolname}"]'
        try:
            options = self.driver.execute_async_script("""
                var callback = arguments[arguments.length - 1];
                var selector = arguments[0];
                var dd = document.querySelector(selector);
                if (!dd) { callback([]); return; }

                // Cliquer sur le div.p-dropdown (le handler Angular est là)
                var clickTarget = dd.querySelector('div.p-dropdown');
                if (!clickTarget) clickTarget = dd.querySelector('.p-dropdown-trigger');
                if (!clickTarget) clickTarget = dd;
                clickTarget.click();

                var attempts = 0;
                var maxAttempts = 30; // 30 × 200ms = 6 secondes max

                function poll() {
                    attempts++;

                    // Chercher les items rendus — dans le p-dropdown ET globalement
                    var items = dd.querySelectorAll('li[role="option"], li.p-dropdown-item, li.p-element, p-dropdownitem li');
                    if (items.length === 0) {
                        // Chercher globalement (overlay peut être hors du p-dropdown)
                        items = document.querySelectorAll('.p-dropdown-panel li, .p-dropdown-items li, .p-overlay-open li[role="option"]');
                    }
                    if (items.length === 0) {
                        // Encore plus large
                        items = document.querySelectorAll('ul[role="listbox"] li');
                    }

                    if (items.length > 0) {
                        var results = [];
                        items.forEach(function(li, i) {
                            var text = li.textContent.trim();
                            if (text && text.length > 1) {
                                results.push({id: String(i), name: text});
                            }
                        });
                        // Fermer le dropdown
                        document.body.click();
                        callback(results);
                    } else if (attempts < maxAttempts) {
                        setTimeout(poll, 200);
                    } else {
                        // Timeout — essayer de lire le label sélectionné au moins
                        document.body.click();
                        callback([]);
                    }
                }

                setTimeout(poll, 500);
            """, selector)

            if options:
                logger.info("Clic JS + polling réussi pour %s: %d options", formcontrolname, len(options))
            else:
                logger.warning("Clic JS + polling: 0 options pour %s", formcontrolname)
            return options or []
        except Exception as e:
            logger.warning("Clic JS + polling échoué pour %s: %s", formcontrolname, e)
            return []

    def _select_dropdown_by_name(self, formcontrolname, name):
        """Sélectionne une option dans un p-dropdown par son texte visible."""
        selector = f'p-dropdown[formcontrolname="{formcontrolname}"]'
        try:
            # Ouvrir le dropdown via JS
            self._js_click(f'{selector} div.p-dropdown')
            time.sleep(1.5)

            # Chercher et cliquer l'item correspondant via JS
            found = self.driver.execute_async_script("""
                var callback = arguments[arguments.length - 1];
                var targetName = arguments[0];
                var attempts = 0;

                function tryFind() {
                    attempts++;
                    var items = document.querySelectorAll(
                        'li[role="option"], li.p-dropdown-item, li.p-element, .p-dropdown-items li, ul[role="listbox"] li'
                    );

                    for (var i = 0; i < items.length; i++) {
                        var text = items[i].textContent.trim();
                        if (text && (text.indexOf(targetName) !== -1 || targetName.indexOf(text) !== -1)) {
                            items[i].click();
                            callback(true);
                            return;
                        }
                    }

                    if (attempts < 20) {
                        setTimeout(tryFind, 200);
                    } else {
                        document.body.click();
                        callback(false);
                    }
                }
                setTimeout(tryFind, 300);
            """, name)

            if found:
                time.sleep(0.5)
                return True

            logger.warning("Option '%s' non trouvée dans %s", name, formcontrolname)
            return False
        except Exception as e:
            logger.warning("Sélection échouée pour '%s' dans %s: %s", name, formcontrolname, e)
            return False

    def _select_dropdown_by_index(self, formcontrolname, index):
        """Sélectionne une option dans un p-dropdown par son index."""
        selector = f'p-dropdown[formcontrolname="{formcontrolname}"]'
        try:
            self._js_click(f'{selector} div.p-dropdown')
            time.sleep(1.5)

            found = self.driver.execute_async_script("""
                var callback = arguments[arguments.length - 1];
                var targetIdx = arguments[0];
                var attempts = 0;

                function tryFind() {
                    attempts++;
                    var items = document.querySelectorAll(
                        'li[role="option"], li.p-dropdown-item, li.p-element, .p-dropdown-items li, ul[role="listbox"] li'
                    );

                    if (items.length > targetIdx) {
                        items[targetIdx].click();
                        callback(true);
                        return;
                    }

                    if (attempts < 20) {
                        setTimeout(tryFind, 200);
                    } else {
                        document.body.click();
                        callback(false);
                    }
                }
                setTimeout(tryFind, 300);
            """, int(index))

            if found:
                time.sleep(0.5)
                return True
            return False
        except Exception as e:
            logger.warning("Sélection par index échouée pour %s[%s]: %s", formcontrolname, index, e)
            return False

    def _ensure_checkbox_checked(self):
        """S'assure que si_tribunaux_primaires est coché."""
        try:
            container = self.driver.find_element(
                By.CSS_SELECTOR,
                'p-checkbox[formcontrolname="si_tribunaux_primaires"]'
            )
            checkbox_div = container.find_element(By.CSS_SELECTOR, '.p-checkbox')
            is_checked = 'p-checkbox-checked' in (checkbox_div.get_attribute('class') or '')
            if not is_checked:
                box = container.find_element(By.CSS_SELECTOR, '.p-checkbox-box')
                box.click()
                time.sleep(2)
        except NoSuchElementException:
            logger.warning("Checkbox si_tribunaux_primaires non trouvée")

    def _ensure_checkbox_unchecked(self):
        """S'assure que si_tribunaux_primaires est décoché."""
        try:
            container = self.driver.find_element(
                By.CSS_SELECTOR,
                'p-checkbox[formcontrolname="si_tribunaux_primaires"]'
            )
            checkbox_div = container.find_element(By.CSS_SELECTOR, '.p-checkbox')
            is_checked = 'p-checkbox-checked' in (checkbox_div.get_attribute('class') or '')
            if is_checked:
                box = container.find_element(By.CSS_SELECTOR, '.p-checkbox-box')
                box.click()
                time.sleep(2)
        except NoSuchElementException:
            pass

    # ------------------------------------------------------------------
    # fetch_tribunal_ids
    # ------------------------------------------------------------------

    def _is_browser_alive(self):
        """Vérifie que le navigateur Chrome est toujours ouvert."""
        try:
            _ = self.driver.title
            return True
        except Exception:
            return False

    def fetch_tribunal_ids(self, progress_callback=None):
        """
        Récupère tous les tribunaux depuis mahakim.ma.

        Args:
            progress_callback: callable(phase, current, total, name, message)
                phase: "appel" | "premiere_instance" | "done" | "error"
                current: numéro courant (1-based)
                total: total des éléments
                name: nom du tribunal en cours
                message: message descriptif

        Returns:
            dict: {
                "appel": [{id, name}, ...],
                "premiere_instance": [{id, name, parent_appel_name}, ...],
                "errors": [str, ...]
            }
        """
        if not self.driver:
            self._create_driver()

        result = {"appel": [], "premiere_instance": [], "errors": []}

        def _notify(phase, current, total, name="", message=""):
            if progress_callback:
                try:
                    progress_callback(phase, current, total, name, message)
                except Exception:
                    pass

        try:
            _notify("init", 0, 0, "", "جاري فتح بوابة محاكم...")
            logger.info("Navigation vers mahakim.ma pour récupérer les IDs des tribunaux")
            self.driver.get(MAHAKIM_URL)
            self._wait_for_angular()

            # Remplir mark pour déclencher le chargement du dropdown tribunal
            self._fill_input("mark", "1604")
            time.sleep(3)

            # --- Étape 1: Extraire les cours d'appel ---
            _notify("init", 0, 0, "", "جاري استخراج محاكم الاستئناف...")
            appel_options = self._extract_dropdown_options("tribunal")
            if appel_options:
                result["appel"] = appel_options
                logger.info("Trouvé %d cours d'appel", len(appel_options))
            else:
                logger.warning("Aucune cour d'appel trouvée")
                result["errors"].append("لم يتم العثور على أي محكمة استئناف")
                _notify("error", 0, 0, "", "لم يتم العثور على أي محكمة استئناف")
                return result

            # --- Étape 2: Cocher la checkbox pour afficher le 2e dropdown ---
            self._ensure_checkbox_checked()

            total_appel = len(appel_options)

            # --- Étape 3: Pour chaque cour d'appel, extraire les tribunaux de 1ère instance ---
            for i, court in enumerate(appel_options):
                court_name = court["name"]
                logger.info(
                    "Sélection cour d'appel %d/%d: %s",
                    i + 1, total_appel, court_name
                )
                _notify("appel", i + 1, total_appel, court_name,
                        f"مزامنة محكمة الاستئناف {i + 1}/{total_appel}: {court_name}")

                # Vérifier que le navigateur est toujours ouvert
                if not self._is_browser_alive():
                    err = "تم إغلاق المتصفح بشكل غير متوقع"
                    result["errors"].append(err)
                    logger.error(err)
                    _notify("error", i + 1, total_appel, court_name, err)
                    break

                try:
                    # Vider les logs avant de déclencher un nouvel appel API
                    self._flush_perf_logs()

                    # Sélectionner cette cour d'appel
                    selected = self._select_dropdown_by_name("tribunal", court_name)
                    if not selected:
                        selected = self._select_dropdown_by_index("tribunal", court.get("id", str(i)))
                    if not selected:
                        logger.warning("Impossible de sélectionner: %s", court_name)
                        result["errors"].append(f"تعذر اختيار: {court_name}")
                        continue

                    # Attendre la réponse API pour les tribunaux de 1ère instance
                    time.sleep(3)

                    # Lire les données réseau capturées
                    pi_options = self._extract_dropdown_options("tribunaux_primaires")
                    if pi_options:
                        for opt in pi_options:
                            opt["parent_appel_name"] = court_name
                        result["premiere_instance"].extend(pi_options)
                        logger.info(
                            "  → %d tribunaux de 1ère instance sous %s",
                            len(pi_options), court_name
                        )
                    else:
                        logger.info("  → Aucun tribunal de 1ère instance sous %s", court_name)

                except TimeoutException:
                    err = f"انتهت مهلة الانتظار عند {court_name}"
                    result["errors"].append(err)
                    logger.error("Timeout for court %s", court_name)
                    continue

                except WebDriverException as e:
                    err_str = str(e)
                    if "no such window" in err_str or "web view not found" in err_str:
                        err = "تم إغلاق المتصفح بشكل غير متوقع"
                        result["errors"].append(err)
                        logger.error("Browser closed: %s", e)
                        _notify("error", i + 1, total_appel, court_name, err)
                        break
                    else:
                        err = f"خطأ في المتصفح عند {court_name}: {err_str[:100]}"
                        result["errors"].append(err)
                        logger.error("WebDriver error for %s: %s", court_name, e)
                        continue

                except Exception as e:
                    err = f"خطأ غير متوقع عند {court_name}: {str(e)[:100]}"
                    result["errors"].append(err)
                    logger.exception("Error for court %s", court_name)
                    continue

        except TimeoutException:
            err = "انتهت مهلة الانتظار — الموقع لا يستجيب"
            result["errors"].append(err)
            logger.error("Timeout en récupérant les IDs des tribunaux")
            _notify("error", 0, 0, "", err)
        except WebDriverException as e:
            err_str = str(e)
            if "no such window" in err_str or "web view not found" in err_str:
                err = "تم إغلاق المتصفح بشكل غير متوقع"
            elif "ERR_INTERNET_DISCONNECTED" in err_str or "ERR_NAME_NOT_RESOLVED" in err_str:
                err = "لا يوجد اتصال بالإنترنت أو الموقع غير متاح"
            else:
                err = f"خطأ في المتصفح: {err_str[:150]}"
            result["errors"].append(err)
            logger.error("WebDriver error lors de fetch_tribunal_ids: %s", e)
            _notify("error", 0, 0, "", err)
        except Exception as e:
            err = f"خطأ غير متوقع: {str(e)[:150]}"
            result["errors"].append(err)
            logger.exception("Erreur inattendue dans fetch_tribunal_ids: %s", e)
            _notify("error", 0, 0, "", err)

        _notify("done", len(result["appel"]),
                len(result["premiere_instance"]), "",
                f"تم: {len(result['appel'])} استئناف، {len(result['premiere_instance'])} ابتدائية")

        logger.info(
            "Résultat: %d cours d'appel, %d tribunaux de 1ère instance, %d erreurs",
            len(result["appel"]), len(result["premiere_instance"]), len(result["errors"])
        )
        return result

    # ------------------------------------------------------------------
    # scrape_affaire
    # ------------------------------------------------------------------

    def scrape_affaire(self, numero, code_categorie, annee,
                       id_mahakim_tribunal=None, is_premiere_instance=False,
                       nom_tribunal=None, nom_tribunal_appel=None):
        """
        Recherche une affaire sur mahakim.ma.

        Args:
            numero: رقم الملف
            code_categorie: رمز الملف
            annee: السنة
            id_mahakim_tribunal: معرف المحكمة في mahakim.ma (optionnel)
            is_premiere_instance: True si tribunal de 1ère instance
            nom_tribunal: اسم المحكمة بالعربية (pour sélection par nom)
            nom_tribunal_appel: اسم محكمة الاستئناف الأم (pour 1ère instance)
        """
        result = {
            "success": False,
            "statut_mahakim": None,
            "prochaine_audience": None,
            "juge": None,
            "observations": None,
            "raw_html": None,
            "error_message": None,
        }

        if not self.driver:
            self._create_driver()

        try:
            logger.info("Navigation vers mahakim.ma pour %s/%s/%s", numero, code_categorie, annee)
            self.driver.get(MAHAKIM_URL)
            self._wait_for_angular()

            # 1. Remplir le numéro
            self._fill_input("numero", str(numero))
            time.sleep(1)

            # 2. Remplir le code catégorie (mark)
            self._fill_input("mark", str(code_categorie))
            time.sleep(1)

            # 3. Remplir l'année
            self._fill_input("annee", str(annee))
            time.sleep(2)

            # 4. Sélectionner le tribunal
            if is_premiere_instance:
                if nom_tribunal_appel:
                    self._select_dropdown_by_name("tribunal", nom_tribunal_appel)
                    time.sleep(1)

                self._ensure_checkbox_checked()
                time.sleep(2)

                if nom_tribunal:
                    self._select_dropdown_by_name("tribunaux_primaires", nom_tribunal)
                elif id_mahakim_tribunal:
                    self._select_dropdown_by_index("tribunaux_primaires", id_mahakim_tribunal)
            else:
                if nom_tribunal:
                    self._select_dropdown_by_name("tribunal", nom_tribunal)
                elif id_mahakim_tribunal:
                    self._select_dropdown_by_index("tribunal", id_mahakim_tribunal)

            time.sleep(1)

            # 5. Cliquer sur بحث (submit)
            try:
                submit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR, 'button.btn-add[type="submit"], button.btn-add, button[type="submit"]')
                    )
                )
                submit_btn.click()
            except TimeoutException:
                result["error_message"] = "زر البحث غير موجود في الصفحة"
                return result

            # 6. Attendre les résultats
            time.sleep(4)

            # 7. Capturer le HTML brut
            try:
                results_area = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "p-table, .p-datatable, table, .result-container, .card-body"
                    ))
                )
                result["raw_html"] = results_area.get_attribute("outerHTML")
            except TimeoutException:
                result["raw_html"] = self.driver.find_element(
                    By.TAG_NAME, "body"
                ).get_attribute("innerHTML")

            # 8. Parser les résultats
            result.update(self._parse_results())
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب"
            logger.error("Timeout lors du scraping mahakim.ma")
        except WebDriverException as e:
            err_str = str(e)
            if "no such window" in err_str or "web view not found" in err_str:
                result["error_message"] = "تم إغلاق المتصفح بشكل غير متوقع"
            elif "ERR_INTERNET_DISCONNECTED" in err_str or "ERR_NAME_NOT_RESOLVED" in err_str:
                result["error_message"] = "لا يوجد اتصال بالإنترنت أو الموقع غير متاح"
            elif "ERR_CONNECTION_TIMED_OUT" in err_str or "ERR_CONNECTION_REFUSED" in err_str:
                result["error_message"] = "تعذر الاتصال بالموقع — تأكد من اتصالك بالإنترنت"
            else:
                result["error_message"] = f"خطأ في المتصفح: {err_str[:200]}"
            logger.error("WebDriver error: %s", e)
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Erreur inattendue lors du scraping")

        return result

    def _parse_results(self):
        """
        Parse la page de résultats structurée de mahakim.ma.

        Structure HTML attendue:
          div.cm-search-parent
            h5 "بطاقة الملف :"
            div.cm-card-dossier
              div.cm-child-dossier → label + p (المحكمة, نوع الشكاية, رقم, موضوع, تاريخ)
            p-tabview
              tab "لائحة الإجراءات" → p-table (تاريخ, نوع, مرجع)
              tab "لائحة الأطراف" → p-table (الصفة, الاسم, المحامون)
        """
        parsed = {
            "statut_mahakim": None,
            "prochaine_audience": None,
            "juge": None,
            "observations": None,
            "card_info": {},
            "procedures": [],
            "parties": [],
        }

        try:
            # --- 1. Extract structured card info (div.cm-card-dossier) ---
            card_info = self.driver.execute_script("""
                var result = {};
                var children = document.querySelectorAll('.cm-child-dossier');
                children.forEach(function(child) {
                    var label = child.querySelector('.cm-div-label label, label');
                    var value = child.querySelector('.cm-div-value p, .cm-div-value, p');
                    if (label && value) {
                        var key = label.textContent.trim().replace(/[:\\s]+$/, '');
                        var val = value.textContent.trim();
                        if (key && val) result[key] = val;
                    }
                });
                return result;
            """)
            if card_info:
                parsed["card_info"] = card_info

            # --- 2. Extract procedures list (first tab: لائحة الإجراءات) ---
            procedures = self.driver.execute_script("""
                var procs = [];
                // Try clicking the first tab to ensure it's active
                var tabs = document.querySelectorAll('p-tabview li[role="presentation"], .p-tabview-nav li');
                if (tabs.length > 0) tabs[0].click && tabs[0].querySelector('a,span')?.click();

                // Wait a tick for Angular rendering, then parse
                var tables = document.querySelectorAll('p-tabpanel p-table tbody tr, p-tabpanel .p-datatable tbody tr');
                if (tables.length === 0) {
                    // Fallback: first p-table in the page
                    tables = document.querySelectorAll('p-table tbody tr, .p-datatable-tbody tr');
                }
                tables.forEach(function(tr) {
                    var cells = tr.querySelectorAll('td');
                    if (cells.length >= 2) {
                        procs.push({
                            date: (cells[0] || {}).textContent?.trim() || '',
                            type: (cells[1] || {}).textContent?.trim() || '',
                            reference: (cells[2] || {}).textContent?.trim() || ''
                        });
                    }
                });
                return procs;
            """)
            if procedures:
                parsed["procedures"] = procedures

                # Derive statut_mahakim from latest procedure type
                if procedures[0].get("type"):
                    parsed["statut_mahakim"] = procedures[0]["type"]

                # Derive prochaine_audience from procedures dates
                for proc in procedures:
                    date_str = proc.get("date", "")
                    if date_str:
                        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
                            try:
                                parsed["prochaine_audience"] = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                        if parsed["prochaine_audience"]:
                            break

                # Build observations from procedures summary
                obs_parts = []
                for proc in procedures[:10]:
                    parts = [proc.get("date", ""), proc.get("type", ""), proc.get("reference", "")]
                    row_text = " | ".join(p for p in parts if p)
                    if row_text:
                        obs_parts.append(row_text)
                if obs_parts:
                    parsed["observations"] = "\n".join(obs_parts)

            # --- 3. Extract parties list (second tab: لائحة الأطراف) ---
            parties = self.driver.execute_script("""
                var pts = [];
                // Click the second tab
                var tabs = document.querySelectorAll('p-tabview li[role="presentation"], .p-tabview-nav li');
                if (tabs.length > 1) {
                    var link = tabs[1].querySelector('a, span');
                    if (link) link.click();
                }
                return new Promise(function(resolve) {
                    setTimeout(function() {
                        var panels = document.querySelectorAll('p-tabpanel');
                        var panel = panels.length > 1 ? panels[1] : panels[0];
                        if (panel) {
                            var rows = panel.querySelectorAll('p-table tbody tr, .p-datatable tbody tr');
                            rows.forEach(function(tr) {
                                var cells = tr.querySelectorAll('td');
                                if (cells.length >= 2) {
                                    pts.push({
                                        role: (cells[0] || {}).textContent?.trim() || '',
                                        name: (cells[1] || {}).textContent?.trim() || '',
                                        lawyers: (cells[2] || {}).textContent?.trim() || ''
                                    });
                                }
                            });
                        }
                        resolve(pts);
                    }, 800);
                });
            """)
            # execute_script doesn't handle promises, use execute_async_script
            try:
                parties = self.driver.execute_async_script("""
                    var callback = arguments[arguments.length - 1];
                    var pts = [];
                    var tabs = document.querySelectorAll('p-tabview li[role="presentation"], .p-tabview-nav li');
                    if (tabs.length > 1) {
                        var link = tabs[1].querySelector('a, span');
                        if (link) link.click();
                    }
                    setTimeout(function() {
                        var panels = document.querySelectorAll('p-tabpanel');
                        var panel = panels.length > 1 ? panels[1] : panels[0];
                        if (panel) {
                            var rows = panel.querySelectorAll('p-table tbody tr, .p-datatable tbody tr');
                            rows.forEach(function(tr) {
                                var cells = tr.querySelectorAll('td');
                                if (cells.length >= 2) {
                                    pts.push({
                                        role: (cells[0] || {}).textContent?.trim() || '',
                                        name: (cells[1] || {}).textContent?.trim() || '',
                                        lawyers: (cells[2] || {}).textContent?.trim() || ''
                                    });
                                }
                            });
                        }
                        callback(pts);
                    }, 800);
                """)
            except Exception:
                pass
            if parties:
                parsed["parties"] = parties

            # --- 4. Fallback: regex-based extraction if structured parsing found nothing ---
            if not parsed["statut_mahakim"] and not parsed["procedures"]:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                for pattern in [r'الحالة\s*[:\s]*(.+)', r'حالة القضية\s*[:\s]*(.+)']:
                    match = re.search(pattern, page_text)
                    if match:
                        parsed["statut_mahakim"] = match.group(1).strip()[:200]
                        break

                if not parsed["prochaine_audience"]:
                    for pattern in [r'الجلسة القادمة\s*[:\s]*([\d/\-\.]+)', r'تاريخ الجلسة\s*[:\s]*([\d/\-\.]+)']:
                        match = re.search(pattern, page_text)
                        if match:
                            date_str = match.group(1).strip()
                            for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y"):
                                try:
                                    parsed["prochaine_audience"] = datetime.strptime(date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                            break

                for pattern in [r'القاضي\s*[:\s]*(.+)', r'المستشار المقرر\s*[:\s]*(.+)']:
                    match = re.search(pattern, page_text)
                    if match:
                        parsed["juge"] = match.group(1).strip()[:200]
                        break

        except Exception as e:
            logger.warning("Erreur lors du parsing des résultats: %s", e)

        return parsed

    # ------------------------------------------------------------------
    # scrape_sessions — مزامنة جدول الجلسات
    # ------------------------------------------------------------------

    SESSIONS_URL = "https://www.mahakim.ma/#/suivi/horaire-seances"

    def scrape_sessions(self, id_mahakim_tribunal, date_seance,
                        type_seance=None, is_premiere_instance=False,
                        nom_tribunal=None, nom_tribunal_appel=None,
                        progress_callback=None):
        """
        Recherche le programme des audiences sur mahakim.ma.

        Args:
            id_mahakim_tribunal: معرف المحكمة في mahakim.ma
            date_seance: تاريخ الجلسة (str dd/mm/yyyy ou date object)
            type_seance: نوع الجلسة (optionnel)
            is_premiere_instance: True si tribunal de 1ère instance
            nom_tribunal: اسم المحكمة بالعربية
            nom_tribunal_appel: اسم محكمة الاستئناف الأم
            progress_callback: callable(phase, message)
        """
        result = {
            "success": False,
            "sessions": [],
            "raw_html": None,
            "error_message": None,
        }

        def _notify(phase, message=""):
            if progress_callback:
                try:
                    progress_callback(phase, message)
                except Exception:
                    pass

        if not self.driver:
            self._create_driver()

        try:
            _notify("init", "جاري فتح صفحة جدول الجلسات...")
            logger.info("Navigation vers mahakim.ma sessions page")
            self.driver.get(self.SESSIONS_URL)

            # Wait for Angular — the sessions page has different form controls
            wait = WebDriverWait(self.driver, self.timeout)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 'p-dropdown[formcontrolname="tribunal"], '
                 'p-calendar[formcontrolname="date_seance"], '
                 'input[formcontrolname], p-dropdown')
            ))
            time.sleep(2)

            # 1. Optionally select type_seance
            if type_seance:
                try:
                    self._select_dropdown_by_name("type_seance", type_seance)
                    time.sleep(1)
                except Exception:
                    logger.warning("Could not select type_seance: %s", type_seance)
            time.sleep(2)

            # 2. Select tribunal
            _notify("selecting", "جاري اختيار المحكمة...")
            if is_premiere_instance:
                if nom_tribunal_appel:
                    self._select_dropdown_by_name("tribunal", nom_tribunal_appel)
                    time.sleep(1)
                self._ensure_checkbox_checked()
                time.sleep(2)
                if nom_tribunal:
                    self._select_dropdown_by_name("tribunaux_primaires", nom_tribunal)
                elif id_mahakim_tribunal:
                    self._select_dropdown_by_index("tribunaux_primaires", id_mahakim_tribunal)
            else:
                if nom_tribunal:
                    self._select_dropdown_by_name("tribunal", nom_tribunal)
                elif id_mahakim_tribunal:
                    self._select_dropdown_by_index("tribunal", id_mahakim_tribunal)
            time.sleep(1)

            # 3. Set date
            _notify("date", "جاري تعيين التاريخ...")
            if hasattr(date_seance, 'strftime'):
                date_str = date_seance.strftime("%d/%m/%Y")
            else:
                date_str = str(date_seance)

            # Fill the p-calendar input
            try:
                cal_input = self.driver.find_element(
                    By.CSS_SELECTOR,
                    'p-calendar[formcontrolname="date_seance"] input, '
                    'p-calendar input, input[formcontrolname="date_seance"]'
                )
                cal_input.clear()
                cal_input.send_keys(date_str)
                time.sleep(1)
                # Close calendar overlay by clicking outside
                self.driver.execute_script("document.body.click();")
                time.sleep(0.5)
            except NoSuchElementException:
                logger.warning("Calendar input not found for date_seance")



            # 4. Submit
            _notify("searching", "جاري البحث...")
            try:
                submit_btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.CSS_SELECTOR,
                         'button.btn-add[type="submit"], button.btn-add, button[type="submit"]')
                    )
                )
                submit_btn.click()
            except TimeoutException:
                result["error_message"] = "زر البحث غير موجود في الصفحة"
                return result

            # 5. Wait for results
            time.sleep(5)
            _notify("parsing", "جاري تحليل النتائج...")

            # 6. Capture raw HTML
            try:
                results_area = WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "p-table, .p-datatable, table, .result-container"
                    ))
                )
                result["raw_html"] = results_area.get_attribute("outerHTML")
            except TimeoutException:
                result["raw_html"] = self.driver.find_element(
                    By.TAG_NAME, "body"
                ).get_attribute("innerHTML")

            # 7. Parse session results
            result["sessions"] = self._parse_session_results()
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب"
            logger.error("Timeout lors du scraping sessions mahakim.ma")
        except WebDriverException as e:
            err_str = str(e)
            if "no such window" in err_str or "web view not found" in err_str:
                result["error_message"] = "تم إغلاق المتصفح بشكل غير متوقع"
            elif "ERR_INTERNET_DISCONNECTED" in err_str or "ERR_NAME_NOT_RESOLVED" in err_str:
                result["error_message"] = "لا يوجد اتصال بالإنترنت أو الموقع غير متاح"
            else:
                result["error_message"] = f"خطأ في المتصفح: {err_str[:200]}"
            logger.error("WebDriver error: %s", e)
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Erreur inattendue lors du scraping sessions")

        _notify("done", "تم")
        return result

    def _parse_session_results(self):
        """
        Parse session schedule results from mahakim.ma.

        Structure:
        - Main outer table (#pr_id_5): الساعة | القاعة | الشعبة | ملفات الجلسة | الهيئة
        - Click ملفات → sub-table: رقم الملف | تاريخ التسجيل | نوع الإجراء | القرار | تاريخ الجلسة المقبلة | الأطراف
        - Click الأطراف → sub-sub-table: الصفة | اسم الطرف
        - Pagination exists at each sub-table level
        """
        sessions = []
        try:
            # Count main data rows in the outer table
            main_row_count = self.driver.execute_script("""
                var mainTable = document.querySelector('#pr_id_5, p-table');
                if (!mainTable) return 0;
                var tbody = mainTable.querySelector(':scope > div > .p-datatable-wrapper > table > tbody');
                if (!tbody) tbody = mainTable.querySelector('tbody');
                if (!tbody) return 0;
                var count = 0;
                tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                    if (!tr.classList.contains('tr-expand') &&
                        !tr.classList.contains('p-datatable-row-expansion')) count++;
                });
                return count;
            """)
            logger.info("Sessions: found %d main rows", main_row_count or 0)

            if not main_row_count:
                return sessions

            for idx in range(main_row_count):
                # Extract basic fields for this session row
                row_data = self.driver.execute_script("""
                    var mainTable = document.querySelector('#pr_id_5, p-table');
                    var tbody = mainTable.querySelector(':scope > div > .p-datatable-wrapper > table > tbody');
                    if (!tbody) tbody = mainTable.querySelector('tbody');
                    var dataRows = [];
                    tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                        if (!tr.classList.contains('tr-expand') &&
                            !tr.classList.contains('p-datatable-row-expansion')) dataRows.push(tr);
                    });
                    var row = dataRows[arguments[0]];
                    if (!row) return null;
                    var cells = row.querySelectorAll('td');
                    var countText = '';
                    if (cells[3]) {
                        var btn = cells[3].querySelector('button');
                        countText = btn ? btn.textContent.trim() : cells[3].textContent.trim();
                    }
                    return {
                        time: (cells[0] || {}).textContent?.trim() || '',
                        room: (cells[1] || {}).textContent?.trim() || '',
                        division: (cells[2] || {}).textContent?.trim() || '',
                        files_count_text: countText,
                    };
                """, idx)

                if not row_data:
                    continue

                count_text = row_data.get("files_count_text", "0")
                count_match = re.search(r'(\d+)', count_text)
                files_count = int(count_match.group(1)) if count_match else 0

                session = {
                    "time": row_data.get("time", ""),
                    "room": row_data.get("room", ""),
                    "division": row_data.get("division", ""),
                    "files_count": files_count,
                    "files": [],
                }

                # Click the ملفات button to expand sub-table
                clicked = self.driver.execute_script("""
                    var mainTable = document.querySelector('#pr_id_5, p-table');
                    var tbody = mainTable.querySelector(':scope > div > .p-datatable-wrapper > table > tbody');
                    if (!tbody) tbody = mainTable.querySelector('tbody');
                    var dataRows = [];
                    tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                        if (!tr.classList.contains('tr-expand') &&
                            !tr.classList.contains('p-datatable-row-expansion')) dataRows.push(tr);
                    });
                    var row = dataRows[arguments[0]];
                    if (!row) return false;
                    var cells = row.querySelectorAll('td');
                    if (cells[3]) {
                        var btn = cells[3].querySelector('button');
                        if (btn) { btn.click(); return true; }
                    }
                    return false;
                """, idx)

                if clicked:
                    time.sleep(2)
                    # Parse all files from the expanded sub-table (with pagination)
                    session["files"] = self._parse_session_files()

                    # Close the expanded panel
                    self.driver.execute_script("""
                        var expRows = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                        for (var i = 0; i < expRows.length; i++) {
                            if (expRows[i].offsetHeight > 0) {
                                var closeBtn = expRows[i].querySelector('button.btn-table-close');
                                if (!closeBtn) {
                                    var btns = expRows[i].querySelectorAll('button');
                                    for (var b = 0; b < btns.length; b++) {
                                        if (btns[b].textContent.indexOf('إغلاق') !== -1) {
                                            closeBtn = btns[b]; break;
                                        }
                                    }
                                }
                                if (closeBtn) closeBtn.click();
                                break;
                            }
                        }
                    """)
                    time.sleep(1)

                sessions.append(session)

        except Exception as e:
            logger.warning("Erreur parsing session results: %s", e)

        return sessions

    def _parse_session_files(self):
        """
        Parse the files sub-table after clicking ملفات الجلسة.
        Handles pagination. For each file, clicks الأطراف to get parties.

        Returns list of dicts: {numero, date_enregistrement, type_procedure,
                                decision, prochaine_audience, parties: [{sifa, nom}]}
        """
        all_files = []
        page = 1

        while True:
            # Parse visible file rows in the expanded sub-table
            file_count = self.driver.execute_script("""
                // Find the visible expansion row
                var expRow = null;
                var expRows = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                for (var i = 0; i < expRows.length; i++) {
                    if (expRows[i].offsetHeight > 0) { expRow = expRows[i]; break; }
                }
                if (!expRow) return 0;
                var subTable = expRow.querySelector('p-table');
                if (!subTable) return 0;
                var tbody = subTable.querySelector('tbody');
                if (!tbody) return 0;
                var count = 0;
                tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                    if (!tr.classList.contains('tr-expand') &&
                        !tr.classList.contains('p-datatable-row-expansion')) count++;
                });
                return count;
            """)

            if not file_count:
                break

            for fidx in range(file_count):
                file_data = self.driver.execute_script("""
                    var expRow = null;
                    var expRows = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                    for (var i = 0; i < expRows.length; i++) {
                        if (expRows[i].offsetHeight > 0) { expRow = expRows[i]; break; }
                    }
                    if (!expRow) return null;
                    var subTable = expRow.querySelector('p-table');
                    var tbody = subTable.querySelector('tbody');
                    var dataRows = [];
                    tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                        if (!tr.classList.contains('tr-expand') &&
                            !tr.classList.contains('p-datatable-row-expansion')) dataRows.push(tr);
                    });
                    var row = dataRows[arguments[0]];
                    if (!row) return null;
                    var cells = row.querySelectorAll('td');
                    return {
                        numero: (cells[0] || {}).textContent?.trim() || '',
                        date_enregistrement: (cells[1] || {}).textContent?.trim() || '',
                        type_procedure: (cells[2] || {}).textContent?.trim() || '',
                        decision: (cells[3] || {}).textContent?.trim() || '',
                        prochaine_audience: (cells[4] || {}).textContent?.trim() || '',
                    };
                """, fidx)

                if not file_data:
                    continue

                file_entry = {
                    "numero": file_data.get("numero", ""),
                    "date_enregistrement": file_data.get("date_enregistrement", ""),
                    "type_procedure": file_data.get("type_procedure", ""),
                    "decision": file_data.get("decision", ""),
                    "prochaine_audience": file_data.get("prochaine_audience", ""),
                    "parties": [],
                }

                # Click الأطراف button to expand parties
                party_clicked = self.driver.execute_script("""
                    var expRow = null;
                    var expRows = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                    for (var i = 0; i < expRows.length; i++) {
                        if (expRows[i].offsetHeight > 0) { expRow = expRows[i]; break; }
                    }
                    if (!expRow) return false;
                    var subTable = expRow.querySelector('p-table');
                    var tbody = subTable.querySelector('tbody');
                    var dataRows = [];
                    tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                        if (!tr.classList.contains('tr-expand') &&
                            !tr.classList.contains('p-datatable-row-expansion')) dataRows.push(tr);
                    });
                    var row = dataRows[arguments[0]];
                    if (!row) return false;
                    var cells = row.querySelectorAll('td');
                    // الأطراف button is in the last cell
                    var lastCell = cells[cells.length - 1];
                    if (lastCell) {
                        var btn = lastCell.querySelector('button');
                        if (btn && !btn.disabled) { btn.click(); return true; }
                    }
                    return false;
                """, fidx)

                if party_clicked:
                    time.sleep(1)
                    # Parse parties from the expanded sub-sub-table
                    file_entry["parties"] = self._parse_session_parties()

                    # Close parties panel
                    self.driver.execute_script("""
                        // Find the innermost visible expansion row (parties)
                        var allExp = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                        var innermost = null;
                        for (var i = allExp.length - 1; i >= 0; i--) {
                            if (allExp[i].offsetHeight > 0) { innermost = allExp[i]; break; }
                        }
                        if (innermost) {
                            var btn = innermost.querySelector('button.btn-table-close');
                            if (!btn) {
                                var btns = innermost.querySelectorAll('button');
                                for (var b = 0; b < btns.length; b++) {
                                    if (btns[b].textContent.indexOf('إغلاق') !== -1) {
                                        btn = btns[b]; break;
                                    }
                                }
                            }
                            if (btn) btn.click();
                        }
                    """)
                    time.sleep(0.5)

                all_files.append(file_entry)

            # Check if there's a next page in the files sub-table paginator
            has_next = self.driver.execute_script("""
                var expRow = null;
                var expRows = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                for (var i = 0; i < expRows.length; i++) {
                    if (expRows[i].offsetHeight > 0) { expRow = expRows[i]; break; }
                }
                if (!expRow) return false;
                var nextBtn = expRow.querySelector('.p-paginator-next:not(.p-disabled)');
                if (nextBtn) { nextBtn.click(); return true; }
                return false;
            """)

            if has_next:
                page += 1
                time.sleep(1.5)
            else:
                break

        return all_files

    def _parse_session_parties(self):
        """Parse parties from the innermost expanded sub-table (الأطراف)."""
        parties = []
        page = 1
        while True:
            page_parties = self.driver.execute_script("""
                // Find the innermost visible expansion row
                var allExp = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                var innermost = null;
                for (var i = allExp.length - 1; i >= 0; i--) {
                    if (allExp[i].offsetHeight > 0) { innermost = allExp[i]; break; }
                }
                if (!innermost) return [];
                var subTable = innermost.querySelector('p-table');
                if (!subTable) return [];
                var tbody = subTable.querySelector('tbody');
                if (!tbody) return [];
                var result = [];
                tbody.querySelectorAll(':scope > tr').forEach(function(tr) {
                    if (tr.classList.contains('tr-expand') ||
                        tr.classList.contains('p-datatable-row-expansion')) return;
                    var cells = tr.querySelectorAll('td');
                    if (cells.length >= 2) {
                        result.push({
                            sifa: (cells[0] || {}).textContent?.trim() || '',
                            nom: (cells[1] || {}).textContent?.trim() || '',
                        });
                    }
                });
                return result;
            """)

            if page_parties:
                parties.extend(page_parties)

            # Check pagination in parties sub-table
            has_next = self.driver.execute_script("""
                var allExp = document.querySelectorAll('tr.tr-expand, tr.p-datatable-row-expansion');
                var innermost = null;
                for (var i = allExp.length - 1; i >= 0; i--) {
                    if (allExp[i].offsetHeight > 0) { innermost = allExp[i]; break; }
                }
                if (!innermost) return false;
                var nextBtn = innermost.querySelector('.p-paginator-next:not(.p-disabled)');
                if (nextBtn) { nextBtn.click(); return true; }
                return false;
            """)

            if has_next:
                page += 1
                time.sleep(1)
            else:
                break

        return parties

    # ------------------------------------------------------------------
    # المسطرة الغيابية — Procédure par contumace
    # ------------------------------------------------------------------

    CONTUMACE_URL = "https://www.mahakim.ma/#/procedure-contumace"

    def scrape_contumace(self, search_query=None, progress_callback=None,
                         existing_keys=None):
        """
        Scrape la page publique المسطرة الغيابية (procédure par contumace).

        Pour chaque ligne on vérifie d'abord si (numero_dossier, cour_appel) existe
        déjà en BD. Si oui on skip. Sinon on clique sur "التفاصيل" pour récupérer
        le motif complet, puis on ferme et on passe à la ligne suivante.

        En cas d'erreur le navigateur reste ouvert pour diagnostic.

        Args:
            search_query: texte de recherche global (optionnel)
            progress_callback: callable(phase, current_page, total_pages, records_count, message)
            existing_keys: set of (numero_dossier, cour_appel) tuples already in DB
        """
        result = {
            "success": False,
            "records": [],
            "total_pages": 0,
            "error_message": None,
        }

        def _notify(phase, current_page=0, total_pages=0, records_count=0, message=""):
            if progress_callback:
                try:
                    progress_callback(phase, current_page, total_pages, records_count, message)
                except Exception:
                    pass

        if not self.driver:
            self._create_driver()

        try:
            _notify("init", message="جاري فتح صفحة المسطرة الغيابية...")
            logger.info("Navigation vers mahakim.ma contumace page")
            self.driver.get(self.CONTUMACE_URL)

            # Wait for Angular to load the page
            wait = WebDriverWait(self.driver, self.timeout)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR,
                 'p-table, .cm-search-parent, .p-datatable')
            ))
            time.sleep(2)

            # If search query, type it in the global search input
            if search_query:
                _notify("searching", message=f"جاري البحث عن: {search_query}")
                try:
                    search_input = self.driver.find_element(
                        By.CSS_SELECTOR,
                        'input.search-filter-global, input[type="search"], '
                        'input[placeholder*="بحث"], .cm-search-parent input'
                    )
                    search_input.clear()
                    search_input.send_keys(search_query)
                    time.sleep(2)
                except NoSuchElementException:
                    logger.warning("Global search input not found on contumace page")

            # Detect total pages via >> (last page) button
            _notify("init", message="جاري حساب عدد الصفحات...")
            total_pages = self._contumace_get_total_pages()
            if total_pages == 0:
                total_pages = 1
            result["total_pages"] = total_pages

            _existing = existing_keys or set()
            all_records = []
            skipped = 0

            for page_num in range(1, total_pages + 1):
                _notify("page", page_num, total_pages, len(all_records),
                        f"جاري تحليل الصفحة {page_num} من {total_pages}..."
                        + (f" (تم تجاوز {skipped})" if skipped else ""))

                # Parse current page rows (with details expansion, skipping existing)
                page_records, page_skipped = self._parse_contumace_page(_existing)
                all_records.extend(page_records)
                skipped += page_skipped

                _notify("page", page_num, total_pages, len(all_records),
                        f"تم تحليل الصفحة {page_num} — {len(all_records)} جديد"
                        + (f" / {skipped} موجود" if skipped else ""))

                # Go to next page if not last
                if page_num < total_pages:
                    try:
                        next_btn = self.driver.find_element(
                            By.CSS_SELECTOR, '.p-paginator-next:not(.p-disabled)'
                        )
                        next_btn.click()
                        time.sleep(2)
                    except NoSuchElementException:
                        logger.warning("Next page button not found at page %d", page_num)
                        break

            result["records"] = all_records
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب. المتصفح مفتوح للتشخيص."
            logger.error("Timeout lors du scraping contumace mahakim.ma")
        except WebDriverException as e:
            err_str = str(e)
            if "no such window" in err_str or "web view not found" in err_str:
                result["error_message"] = "تم إغلاق المتصفح بشكل غير متوقع"
            elif "ERR_INTERNET_DISCONNECTED" in err_str or "ERR_NAME_NOT_RESOLVED" in err_str:
                result["error_message"] = "لا يوجد اتصال بالإنترنت أو الموقع غير متاح"
            else:
                result["error_message"] = f"خطأ في المتصفح: {err_str[:200]}"
            logger.error("WebDriver error contumace: %s", e)
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Erreur inattendue lors du scraping contumace")

        _notify("done", result.get("total_pages", 0), result.get("total_pages", 0),
                len(result["records"]), "تم")
        return result

    def _contumace_get_total_pages(self):
        """
        Get total page count by clicking >> (last page) button in the PrimeNG
        paginator, reading the last page number, then clicking << to go back
        to page 1.
        """
        try:
            # Check if paginator exists at all
            paginators = self.driver.find_elements(By.CSS_SELECTOR, '.p-paginator')
            if not paginators:
                return 1

            # Click >> (go to last page) to reveal the real last page number
            last_btn = self.driver.find_elements(
                By.CSS_SELECTOR, '.p-paginator-last:not(.p-disabled)'
            )
            if last_btn:
                last_btn[0].click()
                time.sleep(2)

                # Now the last page button should be highlighted — read its number
                highlighted = self.driver.find_elements(
                    By.CSS_SELECTOR, '.p-paginator-page.p-highlight'
                )
                if highlighted:
                    last_text = highlighted[0].text.strip()
                    if last_text.isdigit():
                        total = int(last_text)

                        # Go back to page 1 via << (first page) button
                        first_btn = self.driver.find_elements(
                            By.CSS_SELECTOR, '.p-paginator-first:not(.p-disabled)'
                        )
                        if first_btn:
                            first_btn[0].click()
                            time.sleep(2)

                        return total

                # Fallback: read all visible page buttons and take the max
                page_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, '.p-paginator-page'
                )
                if page_buttons:
                    max_page = 1
                    for btn in page_buttons:
                        txt = btn.text.strip()
                        if txt.isdigit():
                            max_page = max(max_page, int(txt))

                    # Go back to page 1
                    first_btn = self.driver.find_elements(
                        By.CSS_SELECTOR, '.p-paginator-first:not(.p-disabled)'
                    )
                    if first_btn:
                        first_btn[0].click()
                        time.sleep(2)

                    return max_page
            else:
                # No >> button means all pages fit in the paginator bar
                page_buttons = self.driver.find_elements(
                    By.CSS_SELECTOR, '.p-paginator-page'
                )
                if page_buttons:
                    last_text = page_buttons[-1].text.strip()
                    if last_text.isdigit():
                        return int(last_text)
                    return len(page_buttons)

        except Exception as e:
            logger.warning("Error detecting contumace pagination: %s", e)
        return 1

    def _parse_contumace_page(self, existing_keys=None):
        """
        Parse all contumace rows on the current page.
        For each row: extract basic fields, check if (numero_dossier, cour_appel)
        already exists in existing_keys. If yes, skip. If no, click التفاصيل
        to get motif, close, next row.

        Returns: (records_list, skipped_count)
        """
        records = []
        skipped = 0
        _existing = existing_keys or set()
        try:
            # Count how many data rows on this page
            row_count = self.driver.execute_script("""
                var count = 0;
                var rows = document.querySelectorAll('p-table tbody tr');
                rows.forEach(function(tr) {
                    if (!tr.classList.contains('tr-expand') &&
                        !tr.classList.contains('p-datatable-row-expansion')) {
                        count++;
                    }
                });
                return count;
            """)

            if not row_count:
                return records, skipped

            for idx in range(row_count):
                # Extract basic fields for this row
                row_data = self.driver.execute_script("""
                    var dataRows = [];
                    var rows = document.querySelectorAll('p-table tbody tr');
                    rows.forEach(function(tr) {
                        if (!tr.classList.contains('tr-expand') &&
                            !tr.classList.contains('p-datatable-row-expansion')) {
                            dataRows.push(tr);
                        }
                    });
                    var row = dataRows[arguments[0]];
                    if (!row) return null;
                    var cells = row.querySelectorAll('td');
                    if (cells.length < 6) return null;
                    return {
                        cour_appel: (cells[0] || {}).textContent?.trim() || '',
                        numero_dossier: (cells[1] || {}).textContent?.trim() || '',
                        nom_accuse: (cells[2] || {}).textContent?.trim() || '',
                        nom_pere: (cells[3] || {}).textContent?.trim() || '',
                        nom_mere: (cells[4] || {}).textContent?.trim() || '',
                        numero_carte: (cells[5] || {}).textContent?.trim() || '',
                    };
                """, idx)

                if not row_data:
                    continue

                # Check if this record already exists in DB — skip if so
                key = (row_data.get("numero_dossier", ""), row_data.get("cour_appel", ""))
                if key[0] and key in _existing:
                    skipped += 1
                    logger.debug("Skipping existing record: %s", key)
                    continue

                record = {
                    "cour_appel": row_data.get("cour_appel", ""),
                    "numero_dossier": row_data.get("numero_dossier", ""),
                    "nom_accuse": row_data.get("nom_accuse", ""),
                    "nom_pere": row_data.get("nom_pere", ""),
                    "nom_mere": row_data.get("nom_mere", ""),
                    "numero_carte": row_data.get("numero_carte", ""),
                    "details_text": "",
                }

                # Click the "التفاصيل" button for this row to expand details
                try:
                    clicked = self.driver.execute_script("""
                        var dataRows = [];
                        var rows = document.querySelectorAll('p-table tbody tr');
                        rows.forEach(function(tr) {
                            if (!tr.classList.contains('tr-expand') &&
                                !tr.classList.contains('p-datatable-row-expansion')) {
                                dataRows.push(tr);
                            }
                        });
                        var row = dataRows[arguments[0]];
                        if (!row) return false;
                        // Find the details button (last td usually has the button)
                        var cells = row.querySelectorAll('td');
                        var lastCell = cells[cells.length - 1];
                        var btn = lastCell ? lastCell.querySelector('button, a') : null;
                        if (!btn) {
                            // Try any button in the row
                            btn = row.querySelector('button, a[class*="detail"], a[class*="expand"]');
                        }
                        if (btn) {
                            btn.click();
                            return true;
                        }
                        return false;
                    """, idx)

                    if clicked:
                        time.sleep(1)  # Wait for expansion animation

                        # Extract the expanded details/motif text
                        expanded_text = self.driver.execute_script("""
                            // Find the currently visible expansion row
                            var expandRows = document.querySelectorAll(
                                'tr.tr-expand, tr.p-datatable-row-expansion'
                            );
                            var texts = [];
                            for (var i = 0; i < expandRows.length; i++) {
                                var er = expandRows[i];
                                if (er.offsetHeight > 0 && er.offsetParent !== null) {
                                    // Try specific contumace class first
                                    var container = er.querySelector('.cm-dossier-procedurecontumace');
                                    if (container) {
                                        // Get all paragraph text
                                        var paras = container.querySelectorAll('p');
                                        if (paras.length > 0) {
                                            paras.forEach(function(p) {
                                                var t = p.textContent?.trim();
                                                if (t) texts.push(t);
                                            });
                                        } else {
                                            // No <p> tags, get the container text directly
                                            var t = container.textContent?.trim();
                                            if (t) texts.push(t);
                                        }
                                    } else {
                                        // Fallback: get all text from expansion row
                                        var allP = er.querySelectorAll('p, div.text-justify, div.details-content');
                                        if (allP.length > 0) {
                                            allP.forEach(function(el) {
                                                var t = el.textContent?.trim();
                                                if (t && t.length > 10) texts.push(t);
                                            });
                                        }
                                        if (texts.length === 0) {
                                            var t = er.textContent?.trim();
                                            if (t) texts.push(t);
                                        }
                                    }
                                    break; // Only process the first visible expansion
                                }
                            }
                            return texts.join('\\n');
                        """)
                        record["details_text"] = (expanded_text or "").strip()

                        # Close the expanded row
                        time.sleep(0.5)
                        self.driver.execute_script("""
                            var expandRows = document.querySelectorAll(
                                'tr.tr-expand, tr.p-datatable-row-expansion'
                            );
                            for (var i = 0; i < expandRows.length; i++) {
                                var er = expandRows[i];
                                if (er.offsetHeight > 0 && er.offsetParent !== null) {
                                    // Try close/إغلاق button
                                    var btns = er.querySelectorAll('button');
                                    for (var b = 0; b < btns.length; b++) {
                                        var txt = btns[b].textContent?.trim() || '';
                                        if (txt.indexOf('إغلاق') !== -1 || txt.indexOf('غلق') !== -1) {
                                            btns[b].click();
                                            break;
                                        }
                                    }
                                    // If no labeled close button, click the first button
                                    if (er.offsetHeight > 0) {
                                        var firstBtn = er.querySelector('button');
                                        if (firstBtn) firstBtn.click();
                                    }
                                    break;
                                }
                            }
                        """)
                        time.sleep(1)  # Wait for close animation

                except Exception as e:
                    logger.debug("Could not expand details for row %d: %s", idx, e)

                records.append(record)
                time.sleep(0.5)  # Small pause between rows

        except Exception as e:
            logger.warning("Error parsing contumace page: %s", e)

        return records, skipped

    # ------------------------------------------------------------------
    # حاسبة الرسوم القضائية — caisseenligne.justice.gov.ma
    # ------------------------------------------------------------------

    TAX_CALC_URL = "https://caisseenligne.justice.gov.ma/CalculTaxes/CalculTaxes"

    def scrape_tax_options(self, progress_callback=None):
        """
        Scrape the cascading form options from the tax calculator page.

        Builds a tree:
        {
            "natures": {
                "مدني": {
                    "type_maqal": [
                        {
                            "value": "1", "label": "مدني افتتاحي",
                            "categories": [
                                {
                                    "value": "1", "label": "قضايا مدنية",
                                    "types_qadiya": [
                                        {"value": "1", "label": "..."}
                                    ]
                                }
                            ]
                        }
                    ]
                },
                ...
            },
            "types_talab": [{"value": "...", "label": "..."}]
        }

        Returns:
            dict with success, options_tree, error_message
        """
        result = {
            "success": False,
            "options_tree": {},
            "error_message": None,
        }

        def _notify(message):
            if progress_callback:
                try:
                    progress_callback(message)
                except Exception:
                    pass

        if not self.driver:
            self._create_driver()

        try:
            _notify("جاري فتح صفحة حاسبة الرسوم...")
            self.driver.get(self.TAX_CALC_URL)
            time.sleep(3)

            # Wait for page to load
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'select, input[type="radio"]'))
            )
            time.sleep(1)

            # --- Extract nature radio buttons ---
            natures = self.driver.execute_script("""
                var radios = document.querySelectorAll('input[type="radio"]');
                var result = [];
                radios.forEach(function(r) {
                    var label = r.parentElement ? r.parentElement.textContent.trim() : '';
                    if (!label) {
                        var lbl = document.querySelector('label[for="' + r.id + '"]');
                        if (lbl) label = lbl.textContent.trim();
                    }
                    result.push({value: r.value, label: label, id: r.id, name: r.name});
                });
                return result;
            """)
            logger.info("Tax calc: found %d nature radios", len(natures or []))

            # --- Extract types_talab (نوع الطلب) — usually independent ---
            types_talab = self._tax_get_select_options_by_position(-1)

            tree = {"natures": {}, "types_talab": types_talab}

            # --- For each nature, click radio and explore cascading selects ---
            for nat in (natures or []):
                nat_label = nat.get("label", "").strip()
                nat_id = nat.get("id", "")
                if not nat_label:
                    continue

                _notify(f"جاري استكشاف: {nat_label}...")

                # Click the radio
                self.driver.execute_script(f"""
                    var r = document.getElementById('{nat_id}');
                    if (r) r.click();
                """)
                time.sleep(1.5)

                # Get نوع المقال options (first select)
                type_maqal_options = self._tax_get_select_options_by_position(0)
                logger.info("Tax calc: nature '%s' → %d type_maqal options",
                            nat_label, len(type_maqal_options))

                nat_data = []

                for tm_opt in type_maqal_options:
                    tm_val = tm_opt.get("value", "")
                    tm_label = tm_opt.get("label", "")
                    if not tm_val or tm_label == 'اختيار':
                        continue

                    _notify(f"{nat_label} → {tm_label}...")

                    # Select this type_maqal
                    self._tax_select_option_by_position(0, tm_val)
                    time.sleep(1)

                    # Get صنف القضية options (second select)
                    categories = self._tax_get_select_options_by_position(1)

                    cat_data = []
                    for cat_opt in categories:
                        cat_val = cat_opt.get("value", "")
                        cat_label = cat_opt.get("label", "")
                        if not cat_val or cat_label == 'اختيار':
                            continue

                        # Select this category
                        self._tax_select_option_by_position(1, cat_val)
                        time.sleep(0.8)

                        # Get نوع القضية options (third select)
                        types_qadiya = self._tax_get_select_options_by_position(2)
                        types_qadiya = [
                            t for t in types_qadiya
                            if t.get("value") and t.get("label") != 'اختيار'
                        ]

                        cat_data.append({
                            "value": cat_val,
                            "label": cat_label,
                            "types_qadiya": types_qadiya,
                        })

                    nat_data.append({
                        "value": tm_val,
                        "label": tm_label,
                        "categories": cat_data,
                    })

                tree["natures"][nat_label] = {"type_maqal": nat_data}

            result["options_tree"] = tree
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب"
            logger.error("Timeout scraping tax calculator")
        except WebDriverException as e:
            result["error_message"] = f"خطأ في المتصفح: {str(e)[:200]}"
            logger.error("WebDriver error tax calc: %s", e)
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Unexpected error scraping tax calc")

        _notify("تم")
        return result

    def calculate_tax(self, nature, type_maqal, categorie, type_qadiya,
                      type_talab, montant, progress_callback=None):
        """
        Fill the tax calculator form and click Calculate to get the result.

        Returns:
            dict with success, result_html, result_text, error_message
        """
        result = {
            "success": False,
            "result_html": "",
            "result_text": "",
            "error_message": None,
        }

        def _notify(msg):
            if progress_callback:
                try:
                    progress_callback(msg)
                except Exception:
                    pass

        if not self.driver:
            self._create_driver()

        try:
            _notify("جاري فتح حاسبة الرسوم...")
            self.driver.get(self.TAX_CALC_URL)
            time.sleep(3)

            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'select, input[type="radio"]'))
            )
            time.sleep(1)

            # 1. Click nature radio
            _notify("اختيار طبيعة الاستخلاص...")
            self.driver.execute_script("""
                var radios = document.querySelectorAll('input[type="radio"]');
                var target = arguments[0];
                radios.forEach(function(r) {
                    var label = r.parentElement ? r.parentElement.textContent.trim() : '';
                    if (label.indexOf(target) !== -1) r.click();
                });
            """, nature)
            time.sleep(1.5)

            # 2. Select نوع المقال
            _notify("اختيار نوع المقال...")
            self._tax_select_option_by_position(0, type_maqal)
            time.sleep(1)

            # 3. Select صنف القضية
            _notify("اختيار صنف القضية...")
            self._tax_select_option_by_position(1, categorie)
            time.sleep(1)

            # 4. Select نوع القضية
            _notify("اختيار نوع القضية...")
            self._tax_select_option_by_position(2, type_qadiya)
            time.sleep(1)

            # 5. Select نوع الطلب
            _notify("اختيار نوع الطلب...")
            self._tax_select_option_by_position(-1, type_talab)
            time.sleep(0.5)

            # 6. Fill montant
            _notify("إدخال المبلغ...")
            self.driver.execute_script("""
                var inputs = document.querySelectorAll('input[type="text"], input[type="number"]');
                for (var i = 0; i < inputs.length; i++) {
                    var inp = inputs[i];
                    var parent = inp.closest('div, td, label');
                    var txt = parent ? parent.textContent : '';
                    if (txt.indexOf('المبلغ') !== -1 || txt.indexOf('مبلغ') !== -1
                        || (inp.name && inp.name.toLowerCase().indexOf('montant') !== -1)) {
                        inp.value = '';
                        inp.focus();
                        inp.value = arguments[0];
                        inp.dispatchEvent(new Event('input', {bubbles: true}));
                        inp.dispatchEvent(new Event('change', {bubbles: true}));
                        break;
                    }
                }
            """, str(montant))
            time.sleep(0.5)

            # 7. Click Calculate
            _notify("جاري الحساب...")
            self.driver.execute_script("""
                var btns = document.querySelectorAll('button, input[type="submit"], input[type="button"]');
                for (var i = 0; i < btns.length; i++) {
                    var txt = btns[i].textContent || btns[i].value || '';
                    if (txt.indexOf('حساب') !== -1 || txt.indexOf('=') !== -1) {
                        btns[i].click();
                        break;
                    }
                }
            """)
            time.sleep(3)

            # 8. Read result
            result_data = self.driver.execute_script("""
                var tables = document.querySelectorAll('table');
                for (var i = 0; i < tables.length; i++) {
                    var t = tables[i];
                    if (t.textContent.indexOf('المجموع') !== -1
                        || t.textContent.indexOf('الرسم') !== -1
                        || t.textContent.indexOf('الضريبة') !== -1) {
                        return {html: t.outerHTML, text: t.textContent.trim()};
                    }
                }
                var resultDiv = document.querySelector('.result, .results, #result, [class*="result"]');
                if (resultDiv) {
                    return {html: resultDiv.outerHTML, text: resultDiv.textContent.trim()};
                }
                return {html: '', text: document.body.textContent.substring(0, 2000)};
            """)

            result["result_html"] = (result_data or {}).get("html", "")
            result["result_text"] = (result_data or {}).get("text", "")
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب"
        except WebDriverException as e:
            result["error_message"] = f"خطأ في المتصفح: {str(e)[:200]}"
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Error calculating tax")

        _notify("تم")
        return result

    # --- Tax calc helpers ---

    def _tax_get_select_options_by_position(self, position):
        """Get all <option> values from the Nth <select> on the page.
        position=-1 means the last select."""
        try:
            return self.driver.execute_script("""
                var selects = document.querySelectorAll('select');
                var idx = arguments[0];
                if (idx < 0) idx = selects.length + idx;
                if (idx < 0 || idx >= selects.length) return [];
                var sel = selects[idx];
                var opts = [];
                for (var i = 0; i < sel.options.length; i++) {
                    opts.push({
                        value: sel.options[i].value,
                        label: sel.options[i].textContent.trim()
                    });
                }
                return opts;
            """, position) or []
        except Exception as e:
            logger.warning("Error getting select options at position %d: %s", position, e)
            return []

    def _tax_select_option_by_position(self, position, value):
        """Select an option by value in the Nth <select>."""
        try:
            self.driver.execute_script("""
                var selects = document.querySelectorAll('select');
                var idx = arguments[0];
                var val = arguments[1];
                if (idx < 0) idx = selects.length + idx;
                if (idx < 0 || idx >= selects.length) return;
                var sel = selects[idx];
                sel.value = val;
                sel.dispatchEvent(new Event('change', {bubbles: true}));
            """, position, value)
        except Exception as e:
            logger.warning("Error selecting option %s at position %d: %s", value, position, e)
