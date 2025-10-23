# =============================================
# Choices — القيم المخزّنة بالفرنسية، التسميات المعروضة بالعربية
# =============================================
insert into TypeAffaires values(  'Pénal', 'جنائي') ,(  'Pénal-Flagrant', 'جنائي تلبّسي') ,(  'Pénal-Contravention', 'مخالفة') ,(  'Pénal-Routier', 'جنح السير') ,(  'Civil', 'مدني') ,(  'Location', 'كراء') ,(  'Famille', 'أسرة') ,(  'Social', 'اجتماعي') ,(  'Commercial', 'تجاري') ,(  'Autre', 'أخرى');
insert into StatutAffaires values(  'Ouverte', 'مفتوحة') ,(  'En audience', 'في الجلسات') ,(  'En délibéré', 'في المداولة') ,(  'Jugée', 'محكوم فيها') ,(  'En notification', 'قيد التبليغ') ,(  'En recours', 'قيد الطعن') ,(  'En exécution', 'قيد التنفيذ') ,(  'Clôturée', 'مختتمة') ,(  'Classée', 'محفوظة');
insert into TypeAudiences values(  'Mise en état', 'جلسة تعيين_تهيئة') ,(  'Plaidoirie', 'مرافعة') ,(  'Débat', 'مناقشة') ,(  'Délibéré', 'مداولة') ,(  'Prononcé', 'جلسة النطق') ,(  'Référé', 'استعجالي') ,(  'Injonction', 'أمر بالأداء_إنذار') ,(  'Autre', 'أخرى');

insert into ResultatAudiences values(  'Report', 'تأجيل') ,(  'Mesure ordonnée', 'اتخاذ إجراء') ,(  'Clôture plaidoiries', 'اختتام المرافعات') ,(  'Jugement prononcé', 'صدر الحكم') ,(  'Sans suite', 'بدون متابعة');

insert into TypeMesures values(  'Enquête', 'بحث') ,(  'Expertise', 'خبرة') ,(  'Inspection', 'معاينة') ,(  'Interrogatoire', 'استجواب') ,(  'Témoignage', 'شهادة') ,(  'Confrontation', 'مواجهة') ,(  'Autre', 'إجراء آخر');

insert into StatutMesures values(  'Ordonnée', 'مأمور بها') ,(  'En cours', 'جارٍ') ,(  'Déposée', 'أودِع التقرير') ,(  'Contre-expertise', 'خبرة مضادّة') ,(  'Clôturée', 'مختتمة');

insert into TypeRecourss values(  'Appel', 'استئناف') ,(  'Opposition', 'تعرض') ,(  'Cassation', 'نقض') ,(  'Rétractation', 'مراجعة') ,(  'Autre', 'طعن آخر');

insert into StatutRecourss values(  'En cours', 'جارٍ') ,(  'Rejeté', 'مرفوض') ,(  'Reçu', 'مقبول شكلاً') ,(  'Jugé', 'محكوم') ,(  'Clôturé', 'مختتم');

insert into TypeExecutions values(  'Monétaire', 'تنفيذ مالي') ,(  'Expulsion_Évacuation', 'إفراغ_إخلاء') ,(  'Saisie', 'حجز') ,(  'Autre', 'تنفيذ آخر');

insert into StatutExecutions values(  'En attente', 'بانتظار') ,(  'En cours', 'جارٍ') ,(  'Suspendu', 'موقوف') ,(  'Achevé', 'منتهٍ') ,(  'Infructueux', 'متعذّر');

insert into TypeDepenses values(  'Frais de justice', 'رسوم قضائية') ,(  'Huissier', 'مفوض قضائي') ,(  'Expertise', 'خبرة') ,(  'Déplacement', 'تنقل') ,(  'Frais de dossier', 'مصاريف ملف') ,(  'Autre', 'أخرى');

insert into TypeRecettes values(  'Provision', 'تسبيق') ,(  'Honoraires', 'أتعاب') ,(  'Remboursement frais', 'استرجاع مصاريف') ,(  'Condamnation', 'مبالغ محكوم بها') ,(  'Autre', 'أخرى');

insert into RoleUtilisateurs values(  'Admin', 'مدير') ,(  'Avocat', 'محامٍ') ,(  'Assistant', 'مساعد') ,(  'Stagiaire', 'متدرّب') ,(  'Lecteur', 'قارىء');

insert into StatutTaches values(  'A faire', 'للتنفيذ') ,(  'En cours', 'جارٍ') ,(  'En attente', 'بانتظار') ,(  'Terminé', 'منجز');

insert into TypeAlertes values(  'Audience', 'جلسة') ,(  'Echéance recours', 'أجل الطعن') ,(  'Exécution', 'تنفيذ') ,(  'Dépense', 'مصاريف') ,(  'Autre', 'أخرى');
