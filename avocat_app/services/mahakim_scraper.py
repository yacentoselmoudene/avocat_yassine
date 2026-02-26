# avocat_app/services/mahakim_scraper.py
"""
Service Selenium pour synchroniser les données d'affaires depuis mahakim.ma.
Utilise un navigateur headless Chrome pour scraper le portail officiel des tribunaux marocains.
"""
import logging
import re
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException,
)

logger = logging.getLogger(__name__)

MAHAKIM_URL = "https://www.mahakim.ma/Ar/Services/SuiviAffaires_new/"


class MahakimScraper:
    """Encapsule la logique de scraping du portail mahakim.ma."""

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

    def scrape_affaire(self, numero, code_categorie, annee, type_juridiction=None):
        """
        Recherche une affaire sur mahakim.ma.

        Args:
            numero: رقم الملف (ex: "1234")
            code_categorie: رمز الصنف (ex: "1101")
            annee: السنة (ex: "2026")
            type_juridiction: نوع المحكمة (optionnel)

        Returns:
            dict avec les résultats ou les erreurs
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

            wait = WebDriverWait(self.driver, self.timeout)

            # Attendre le chargement de la page
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "form")))

            # Sélectionner le type de juridiction si disponible
            if type_juridiction:
                try:
                    juridiction_select = wait.until(
                        EC.presence_of_element_located((By.ID, "IdTypeTribunal"))
                    )
                    Select(juridiction_select).select_by_visible_text(type_juridiction)
                    # Attendre le rechargement éventuel
                    import time
                    time.sleep(1)
                except (NoSuchElementException, TimeoutException):
                    logger.warning("Impossible de sélectionner le type de juridiction: %s", type_juridiction)

            # Sélectionner le tribunal
            try:
                tribunal_select = wait.until(
                    EC.presence_of_element_located((By.ID, "IdTribunal"))
                )
                # Le tribunal est souvent auto-sélectionné
            except (NoSuchElementException, TimeoutException):
                pass

            # Saisir le numéro de dossier
            try:
                numero_input = wait.until(
                    EC.presence_of_element_located((By.ID, "NumeroDossier"))
                )
                numero_input.clear()
                numero_input.send_keys(numero)
            except (NoSuchElementException, TimeoutException):
                # Essayer d'autres sélecteurs courants
                try:
                    numero_input = self.driver.find_element(
                        By.CSS_SELECTOR, "input[name*='numero'], input[name*='Numero']"
                    )
                    numero_input.clear()
                    numero_input.send_keys(numero)
                except NoSuchElementException:
                    result["error_message"] = "حقل رقم الملف غير موجود في الصفحة"
                    return result

            # Saisir le code catégorie
            try:
                code_input = wait.until(
                    EC.presence_of_element_located((By.ID, "CodeCategorie"))
                )
                code_input.clear()
                code_input.send_keys(code_categorie)
            except (NoSuchElementException, TimeoutException):
                try:
                    code_input = self.driver.find_element(
                        By.CSS_SELECTOR, "input[name*='code'], input[name*='Code'], select[name*='code']"
                    )
                    if code_input.tag_name == "select":
                        Select(code_input).select_by_value(code_categorie)
                    else:
                        code_input.clear()
                        code_input.send_keys(code_categorie)
                except NoSuchElementException:
                    logger.warning("Champ code catégorie non trouvé, tentative avec référence complète")

            # Saisir l'année
            try:
                annee_input = wait.until(
                    EC.presence_of_element_located((By.ID, "AnneeDossier"))
                )
                annee_input.clear()
                annee_input.send_keys(annee)
            except (NoSuchElementException, TimeoutException):
                try:
                    annee_input = self.driver.find_element(
                        By.CSS_SELECTOR, "input[name*='annee'], input[name*='Annee'], select[name*='annee']"
                    )
                    if annee_input.tag_name == "select":
                        Select(annee_input).select_by_value(annee)
                    else:
                        annee_input.clear()
                        annee_input.send_keys(annee)
                except NoSuchElementException:
                    logger.warning("Champ année non trouvé")

            # Soumettre le formulaire
            try:
                submit_btn = self.driver.find_element(
                    By.CSS_SELECTOR, "button[type='submit'], input[type='submit'], .btn-search, #btnSearch"
                )
                submit_btn.click()
            except NoSuchElementException:
                # Essayer de soumettre le formulaire directement
                form = self.driver.find_element(By.TAG_NAME, "form")
                form.submit()

            # Attendre les résultats
            import time
            time.sleep(3)

            # Capturer le HTML brut de la zone de résultats
            try:
                results_area = wait.until(
                    EC.presence_of_element_located((
                        By.CSS_SELECTOR,
                        "#results, .results, .table-responsive, #divResult, .result-container, table"
                    ))
                )
                result["raw_html"] = results_area.get_attribute("outerHTML")
            except TimeoutException:
                # Prendre tout le body
                result["raw_html"] = self.driver.find_element(By.TAG_NAME, "body").get_attribute("innerHTML")

            # Parser les résultats
            result.update(self._parse_results())
            result["success"] = True

        except TimeoutException:
            result["error_message"] = "انتهت مهلة الانتظار — الموقع لا يستجيب"
            logger.error("Timeout lors du scraping mahakim.ma")
        except WebDriverException as e:
            result["error_message"] = f"خطأ في المتصفح: {str(e)[:200]}"
            logger.error("WebDriver error: %s", e)
        except Exception as e:
            result["error_message"] = f"خطأ غير متوقع: {str(e)[:200]}"
            logger.exception("Erreur inattendue lors du scraping")

        return result

    def _parse_results(self):
        """Parse la page de résultats pour extraire les informations utiles."""
        parsed = {
            "statut_mahakim": None,
            "prochaine_audience": None,
            "juge": None,
            "observations": None,
        }

        try:
            page_text = self.driver.find_element(By.TAG_NAME, "body").text

            # Chercher le statut
            for pattern in [r'الحالة\s*[:\s]*(.+)', r'حالة القضية\s*[:\s]*(.+)', r'Statut\s*[:\s]*(.+)']:
                match = re.search(pattern, page_text)
                if match:
                    parsed["statut_mahakim"] = match.group(1).strip()[:200]
                    break

            # Chercher la prochaine audience
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

            # Chercher le juge
            for pattern in [r'القاضي\s*[:\s]*(.+)', r'المستشار المقرر\s*[:\s]*(.+)', r'الهيئة\s*[:\s]*(.+)']:
                match = re.search(pattern, page_text)
                if match:
                    parsed["juge"] = match.group(1).strip()[:200]
                    break

            # Chercher les observations dans les tableaux
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr")
                obs_parts = []
                for row in rows[:10]:  # Limiter à 10 lignes
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if cells:
                        row_text = " | ".join(c.text.strip() for c in cells if c.text.strip())
                        if row_text:
                            obs_parts.append(row_text)
                if obs_parts:
                    parsed["observations"] = "\n".join(obs_parts)
            except Exception:
                pass

        except Exception as e:
            logger.warning("Erreur lors du parsing des résultats: %s", e)

        return parsed
