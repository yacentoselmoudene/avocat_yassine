# Generated migration for CodeCategorieAffaire model + Affaire structured fields
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def seed_codes(apps, schema_editor):
    CodeCategorieAffaire = apps.get_model('avocat_app', 'CodeCategorieAffaire')
    codes = [
        # === مدني ابتدائي (Civil - Première instance) ===
        ('1101', 'دعوى مدنية عادية', 'civil', 'premiere_instance'),
        ('1102', 'دعوى تعويض عن الضرر', 'civil', 'premiere_instance'),
        ('1103', 'دعوى إفراغ محل سكني', 'civil', 'premiere_instance'),
        ('1104', 'دعوى إفراغ محل تجاري', 'civil', 'premiere_instance'),
        ('1105', 'دعوى قسمة عقار', 'civil', 'premiere_instance'),
        ('1106', 'دعوى استرداد حيازة', 'civil', 'premiere_instance'),
        ('1107', 'دعوى تشويش على الحيازة', 'civil', 'premiere_instance'),
        ('1108', 'دعوى الشفعة', 'civil', 'premiere_instance'),
        ('1109', 'دعوى بطلان عقد', 'civil', 'premiere_instance'),
        ('1110', 'دعوى فسخ عقد', 'civil', 'premiere_instance'),
        ('1111', 'دعوى إتمام البيع', 'civil', 'premiere_instance'),
        ('1112', 'دعوى أداء واجبات الكراء', 'civil', 'premiere_instance'),
        ('1113', 'دعوى مراجعة السومة الكرائية', 'civil', 'premiere_instance'),
        ('1114', 'دعوى إبطال إنذار بالإفراغ', 'civil', 'premiere_instance'),
        ('1115', 'دعوى المسؤولية التقصيرية', 'civil', 'premiere_instance'),
        ('1116', 'دعوى المسؤولية العقدية', 'civil', 'premiere_instance'),
        ('1117', 'دعوى إثبات ملكية', 'civil', 'premiere_instance'),
        ('1118', 'دعوى تحفيظ عقار', 'civil', 'premiere_instance'),
        ('1119', 'دعوى التعرض على تحفيظ', 'civil', 'premiere_instance'),
        ('1120', 'دعوى التقييد بالرسم العقاري', 'civil', 'premiere_instance'),
        ('1121', 'دعوى التشطيب على تقييد', 'civil', 'premiere_instance'),
        ('1122', 'دعوى ارتفاق', 'civil', 'premiere_instance'),
        ('1123', 'دعوى حق السطحية', 'civil', 'premiere_instance'),
        ('1124', 'دعوى الحراسة القضائية', 'civil', 'premiere_instance'),
        ('1125', 'أمر بالأداء', 'civil', 'premiere_instance'),
        ('1126', 'دعوى استعجالية', 'civil', 'premiere_instance'),
        ('1127', 'معاينة واستجواب', 'civil', 'premiere_instance'),
        ('1128', 'خبرة قضائية', 'civil', 'premiere_instance'),
        ('1129', 'دعوى حادثة شغل', 'civil', 'premiere_instance'),
        ('1130', 'دعوى تأمين', 'civil', 'premiere_instance'),
        ('1131', 'دعوى ضد شركة التأمين', 'civil', 'premiere_instance'),
        ('1132', 'دعوى حوادث السير', 'civil', 'premiere_instance'),
        ('1133', 'طلب تعيين خبير', 'civil', 'premiere_instance'),
        ('1134', 'طلب إجراء معاينة', 'civil', 'premiere_instance'),
        ('1135', 'طلب سماع شاهد', 'civil', 'premiere_instance'),
        ('1136', 'دعوى رفع الضرر', 'civil', 'premiere_instance'),
        ('1137', 'دعوى منع من البناء', 'civil', 'premiere_instance'),
        ('1138', 'دعوى هدم بناء', 'civil', 'premiere_instance'),
        ('1139', 'دعوى غصب عقار', 'civil', 'premiere_instance'),
        ('1140', 'دعوى استحقاق', 'civil', 'premiere_instance'),

        # === مدني استئناف (Civil - Appel) ===
        ('1201', 'استئناف حكم مدني', 'civil', 'appel'),
        ('1202', 'استئناف أمر استعجالي', 'civil', 'appel'),
        ('1203', 'استئناف أمر بالأداء', 'civil', 'appel'),
        ('1204', 'استئناف حكم إفراغ', 'civil', 'appel'),
        ('1205', 'استئناف حكم تعويض', 'civil', 'appel'),
        ('1206', 'استئناف حكم قسمة', 'civil', 'appel'),
        ('1207', 'استئناف حكم تحفيظ', 'civil', 'appel'),
        ('1208', 'استئناف حكم شفعة', 'civil', 'appel'),
        ('1209', 'استئناف حكم كراء', 'civil', 'appel'),
        ('1210', 'استئناف حكم حيازة', 'civil', 'appel'),

        # === مدني نقض (Civil - Cassation) ===
        ('1301', 'طعن بالنقض مدني', 'civil', 'cassation'),
        ('1302', 'طعن بالنقض عقاري', 'civil', 'cassation'),
        ('1303', 'طعن بالنقض كرائي', 'civil', 'cassation'),

        # === جنائي ابتدائي (Pénal - Première instance) ===
        ('2101', 'مخالفة', 'penal', 'premiere_instance'),
        ('2102', 'جنحة ضبطية', 'penal', 'premiere_instance'),
        ('2103', 'جنحة تأديبية', 'penal', 'premiere_instance'),
        ('2104', 'جناية', 'penal', 'premiere_instance'),
        ('2105', 'السرقة', 'penal', 'premiere_instance'),
        ('2106', 'النصب والاحتيال', 'penal', 'premiere_instance'),
        ('2107', 'خيانة الأمانة', 'penal', 'premiere_instance'),
        ('2108', 'إصدار شيك بدون رصيد', 'penal', 'premiere_instance'),
        ('2109', 'الضرب والجرح', 'penal', 'premiere_instance'),
        ('2110', 'التهديد', 'penal', 'premiere_instance'),
        ('2111', 'السب والقذف', 'penal', 'premiere_instance'),
        ('2112', 'التزوير واستعمال المزور', 'penal', 'premiere_instance'),
        ('2113', 'تبديد أموال الزوجية', 'penal', 'premiere_instance'),
        ('2114', 'إهمال الأسرة', 'penal', 'premiere_instance'),
        ('2115', 'الخيانة الزوجية', 'penal', 'premiere_instance'),
        ('2116', 'الاتجار في المخدرات', 'penal', 'premiere_instance'),
        ('2117', 'حيازة المخدرات', 'penal', 'premiere_instance'),
        ('2118', 'استهلاك المخدرات', 'penal', 'premiere_instance'),
        ('2119', 'السكر العلني', 'penal', 'premiere_instance'),
        ('2120', 'القتل العمد', 'penal', 'premiere_instance'),
        ('2121', 'القتل غير العمد', 'penal', 'premiere_instance'),
        ('2122', 'حوادث السير الجنحية', 'penal', 'premiere_instance'),
        ('2123', 'السياقة في حالة سكر', 'penal', 'premiere_instance'),
        ('2124', 'الفرار بعد حادثة سير', 'penal', 'premiere_instance'),
        ('2125', 'انتهاك حرمة المسكن', 'penal', 'premiere_instance'),
        ('2126', 'التحرش الجنسي', 'penal', 'premiere_instance'),
        ('2127', 'الاغتصاب', 'penal', 'premiere_instance'),
        ('2128', 'هتك العرض', 'penal', 'premiere_instance'),
        ('2129', 'تعذيب', 'penal', 'premiere_instance'),
        ('2130', 'الرشوة', 'penal', 'premiere_instance'),
        ('2131', 'استغلال النفوذ', 'penal', 'premiere_instance'),
        ('2132', 'الاختلاس', 'penal', 'premiere_instance'),
        ('2133', 'غسل الأموال', 'penal', 'premiere_instance'),
        ('2134', 'الإرهاب', 'penal', 'premiere_instance'),
        ('2135', 'حمل السلاح بدون رخصة', 'penal', 'premiere_instance'),
        ('2136', 'تزوير وثائق رسمية', 'penal', 'premiere_instance'),
        ('2137', 'انتحال صفة', 'penal', 'premiere_instance'),
        ('2138', 'التهريب الجمركي', 'penal', 'premiere_instance'),
        ('2139', 'الغش التجاري', 'penal', 'premiere_instance'),
        ('2140', 'المس بسلامة الطريق', 'penal', 'premiere_instance'),
        ('2141', 'التشرد', 'penal', 'premiere_instance'),
        ('2142', 'التسول', 'penal', 'premiere_instance'),
        ('2143', 'اختطاف', 'penal', 'premiere_instance'),
        ('2144', 'احتجاز', 'penal', 'premiere_instance'),
        ('2145', 'إشعال حريق عمدا', 'penal', 'premiere_instance'),
        ('2146', 'تخريب ممتلكات', 'penal', 'premiere_instance'),
        ('2147', 'عدم تنفيذ حكم قضائي', 'penal', 'premiere_instance'),
        ('2148', 'إهانة موظف عمومي', 'penal', 'premiere_instance'),
        ('2149', 'العنف ضد الأصول', 'penal', 'premiere_instance'),
        ('2150', 'الفساد', 'penal', 'premiere_instance'),

        # === جنائي استئناف (Pénal - Appel) ===
        ('2201', 'استئناف جنحي', 'penal', 'appel'),
        ('2202', 'استئناف جنائي', 'penal', 'appel'),
        ('2203', 'استئناف أمر قاضي التحقيق', 'penal', 'appel'),
        ('2204', 'استئناف قرار غرفة الجنايات', 'penal', 'appel'),
        ('2205', 'استئناف حكم مخالفة', 'penal', 'appel'),

        # === جنائي نقض (Pénal - Cassation) ===
        ('2301', 'طعن بالنقض جنحي', 'penal', 'cassation'),
        ('2302', 'طعن بالنقض جنائي', 'penal', 'cassation'),

        # === أسرة ابتدائي (Famille - Première instance) ===
        ('3101', 'طلب الإذن بالزواج', 'famille', 'premiere_instance'),
        ('3102', 'دعوى الطلاق الاتفاقي', 'famille', 'premiere_instance'),
        ('3103', 'دعوى الطلاق للشقاق', 'famille', 'premiere_instance'),
        ('3104', 'دعوى التطليق للضرر', 'famille', 'premiere_instance'),
        ('3105', 'دعوى التطليق للغيبة', 'famille', 'premiere_instance'),
        ('3106', 'دعوى التطليق لعدم الإنفاق', 'famille', 'premiere_instance'),
        ('3107', 'دعوى التطليق للعيب', 'famille', 'premiere_instance'),
        ('3108', 'دعوى التطليق للإيلاء والهجر', 'famille', 'premiere_instance'),
        ('3109', 'دعوى النفقة', 'famille', 'premiere_instance'),
        ('3110', 'نفقة الأطفال', 'famille', 'premiere_instance'),
        ('3111', 'نفقة الزوجة', 'famille', 'premiere_instance'),
        ('3112', 'نفقة الوالدين', 'famille', 'premiere_instance'),
        ('3113', 'دعوى الحضانة', 'famille', 'premiere_instance'),
        ('3114', 'دعوى إسقاط الحضانة', 'famille', 'premiere_instance'),
        ('3115', 'دعوى حق الزيارة', 'famille', 'premiere_instance'),
        ('3116', 'دعوى إثبات النسب', 'famille', 'premiere_instance'),
        ('3117', 'دعوى نفي النسب', 'famille', 'premiere_instance'),
        ('3118', 'دعوى الكفالة', 'famille', 'premiere_instance'),
        ('3119', 'دعوى الولاية على المال', 'famille', 'premiere_instance'),
        ('3120', 'دعوى الحجر', 'famille', 'premiere_instance'),
        ('3121', 'دعوى رفع الحجر', 'famille', 'premiere_instance'),
        ('3122', 'دعوى الإرث', 'famille', 'premiere_instance'),
        ('3123', 'دعوى قسمة التركة', 'famille', 'premiere_instance'),
        ('3124', 'دعوى الوصية', 'famille', 'premiere_instance'),
        ('3125', 'دعوى التنزيل', 'famille', 'premiere_instance'),
        ('3126', 'دعوى بيت الزوجية', 'famille', 'premiere_instance'),
        ('3127', 'دعوى المتعة', 'famille', 'premiere_instance'),
        ('3128', 'دعوى الصداق', 'famille', 'premiere_instance'),
        ('3129', 'دعوى الرجعة', 'famille', 'premiere_instance'),
        ('3130', 'طلب الإذن بالتعدد', 'famille', 'premiere_instance'),
        ('3131', 'دعوى ثبوت الزوجية', 'famille', 'premiere_instance'),
        ('3132', 'دعوى تقدير نفقة مؤقتة', 'famille', 'premiere_instance'),
        ('3133', 'دعوى مستحقات الأطفال', 'famille', 'premiere_instance'),
        ('3134', 'دعوى أجرة الحضانة', 'famille', 'premiere_instance'),
        ('3135', 'دعوى أجرة الرضاع', 'famille', 'premiere_instance'),
        ('3136', 'دعوى السكنى', 'famille', 'premiere_instance'),
        ('3137', 'دعوى تعديل النفقة', 'famille', 'premiere_instance'),
        ('3138', 'دعوى إسقاط النفقة', 'famille', 'premiere_instance'),
        ('3139', 'دعوى الحالة المدنية', 'famille', 'premiere_instance'),
        ('3140', 'تصحيح عقد الزواج', 'famille', 'premiere_instance'),

        # === أسرة استئناف (Famille - Appel) ===
        ('3201', 'استئناف حكم طلاق', 'famille', 'appel'),
        ('3202', 'استئناف حكم نفقة', 'famille', 'appel'),
        ('3203', 'استئناف حكم حضانة', 'famille', 'appel'),
        ('3204', 'استئناف حكم إرث', 'famille', 'appel'),
        ('3205', 'استئناف حكم نسب', 'famille', 'appel'),
        ('3206', 'استئناف حكم أسري', 'famille', 'appel'),

        # === أسرة نقض ===
        ('3301', 'طعن بالنقض أسري', 'famille', 'cassation'),

        # === تجاري ابتدائي (Commercial - Première instance) ===
        ('4101', 'دعوى تجارية عادية', 'commercial', 'premiere_instance'),
        ('4102', 'دعوى أداء مبلغ تجاري', 'commercial', 'premiere_instance'),
        ('4103', 'دعوى عدم أداء كمبيالة', 'commercial', 'premiere_instance'),
        ('4104', 'دعوى الإفلاس', 'commercial', 'premiere_instance'),
        ('4105', 'دعوى التسوية القضائية', 'commercial', 'premiere_instance'),
        ('4106', 'دعوى التصفية القضائية', 'commercial', 'premiere_instance'),
        ('4107', 'دعوى صعوبة المقاولة', 'commercial', 'premiere_instance'),
        ('4108', 'دعوى فتح مسطرة المعالجة', 'commercial', 'premiere_instance'),
        ('4109', 'دعوى تمديد مسطرة', 'commercial', 'premiere_instance'),
        ('4110', 'دعوى سقوط الأهلية التجارية', 'commercial', 'premiere_instance'),
        ('4111', 'دعوى منافسة غير مشروعة', 'commercial', 'premiere_instance'),
        ('4112', 'دعوى علامة تجارية', 'commercial', 'premiere_instance'),
        ('4113', 'دعوى براءة اختراع', 'commercial', 'premiere_instance'),
        ('4114', 'دعوى حل شركة', 'commercial', 'premiere_instance'),
        ('4115', 'دعوى تعيين مسير مؤقت', 'commercial', 'premiere_instance'),
        ('4116', 'دعوى مسؤولية المسير', 'commercial', 'premiere_instance'),
        ('4117', 'دعوى الأصل التجاري', 'commercial', 'premiere_instance'),
        ('4118', 'دعوى إفراغ محل تجاري', 'commercial', 'premiere_instance'),
        ('4119', 'دعوى تجديد عقد الكراء التجاري', 'commercial', 'premiere_instance'),
        ('4120', 'دعوى التعويض عن الإفراغ', 'commercial', 'premiere_instance'),
        ('4121', 'أمر بالأداء تجاري', 'commercial', 'premiere_instance'),
        ('4122', 'دعوى استعجالية تجارية', 'commercial', 'premiere_instance'),
        ('4123', 'دعوى حجز تحفظي تجاري', 'commercial', 'premiere_instance'),
        ('4124', 'دعوى وكالة تجارية', 'commercial', 'premiere_instance'),
        ('4125', 'دعوى تأمين تجاري', 'commercial', 'premiere_instance'),
        ('4126', 'دعوى نقل بحري', 'commercial', 'premiere_instance'),
        ('4127', 'دعوى نقل بري تجاري', 'commercial', 'premiere_instance'),
        ('4128', 'دعوى بنكية', 'commercial', 'premiere_instance'),
        ('4129', 'دعوى كفالة تجارية', 'commercial', 'premiere_instance'),
        ('4130', 'دعوى رهن تجاري', 'commercial', 'premiere_instance'),

        # === تجاري استئناف ===
        ('4201', 'استئناف حكم تجاري', 'commercial', 'appel'),
        ('4202', 'استئناف أمر بالأداء تجاري', 'commercial', 'appel'),
        ('4203', 'استئناف حكم صعوبة المقاولة', 'commercial', 'appel'),
        ('4204', 'استئناف أمر استعجالي تجاري', 'commercial', 'appel'),
        ('4205', 'استئناف حكم تصفية قضائية', 'commercial', 'appel'),

        # === تجاري نقض ===
        ('4301', 'طعن بالنقض تجاري', 'commercial', 'cassation'),

        # === إداري ابتدائي (Administratif - Première instance) ===
        ('5101', 'دعوى إلغاء قرار إداري', 'administratif', 'premiere_instance'),
        ('5102', 'دعوى التعويض الإداري', 'administratif', 'premiere_instance'),
        ('5103', 'دعوى نزع الملكية', 'administratif', 'premiere_instance'),
        ('5104', 'دعوى الاحتلال المؤقت', 'administratif', 'premiere_instance'),
        ('5105', 'دعوى ضريبية', 'administratif', 'premiere_instance'),
        ('5106', 'دعوى جمركية', 'administratif', 'premiere_instance'),
        ('5107', 'دعوى الوظيفة العمومية', 'administratif', 'premiere_instance'),
        ('5108', 'دعوى تأديبية إدارية', 'administratif', 'premiere_instance'),
        ('5109', 'دعوى العقود الإدارية', 'administratif', 'premiere_instance'),
        ('5110', 'دعوى الصفقات العمومية', 'administratif', 'premiere_instance'),
        ('5111', 'دعوى التعمير', 'administratif', 'premiere_instance'),
        ('5112', 'دعوى رخصة البناء', 'administratif', 'premiere_instance'),
        ('5113', 'دعوى بيئية', 'administratif', 'premiere_instance'),
        ('5114', 'دعوى انتخابية', 'administratif', 'premiere_instance'),
        ('5115', 'استعجالي إداري', 'administratif', 'premiere_instance'),
        ('5116', 'دعوى المسؤولية الإدارية', 'administratif', 'premiere_instance'),
        ('5117', 'طعن في قرار رفض الإقامة', 'administratif', 'premiere_instance'),
        ('5118', 'دعوى ملك الدولة الخاص', 'administratif', 'premiere_instance'),
        ('5119', 'دعوى أملاك الجماعات', 'administratif', 'premiere_instance'),
        ('5120', 'دعوى المياه والغابات', 'administratif', 'premiere_instance'),

        # === إداري استئناف ===
        ('5201', 'استئناف حكم إداري', 'administratif', 'appel'),
        ('5202', 'استئناف أمر استعجالي إداري', 'administratif', 'appel'),
        ('5203', 'استئناف حكم ضريبي', 'administratif', 'appel'),
        ('5204', 'استئناف حكم نزع الملكية', 'administratif', 'appel'),
        ('5205', 'استئناف حكم وظيفة عمومية', 'administratif', 'appel'),

        # === إداري نقض ===
        ('5301', 'طعن بالنقض إداري', 'administratif', 'cassation'),

        # === اجتماعي ابتدائي (Social - Première instance) ===
        ('6101', 'دعوى الفصل التعسفي', 'social', 'premiere_instance'),
        ('6102', 'دعوى الطرد من العمل', 'social', 'premiere_instance'),
        ('6103', 'دعوى الأجور', 'social', 'premiere_instance'),
        ('6104', 'دعوى التعويض عن الإعفاء', 'social', 'premiere_instance'),
        ('6105', 'دعوى التعويض عن مهلة الإخطار', 'social', 'premiere_instance'),
        ('6106', 'دعوى التعويض عن الضرر', 'social', 'premiere_instance'),
        ('6107', 'دعوى التعويض عن العطلة', 'social', 'premiere_instance'),
        ('6108', 'دعوى التعويض عن الأقدمية', 'social', 'premiere_instance'),
        ('6109', 'دعوى حادثة شغل', 'social', 'premiere_instance'),
        ('6110', 'دعوى مرض مهني', 'social', 'premiere_instance'),
        ('6111', 'دعوى الضمان الاجتماعي', 'social', 'premiere_instance'),
        ('6112', 'دعوى التقاعد', 'social', 'premiere_instance'),
        ('6113', 'دعوى التأمين على المرض', 'social', 'premiere_instance'),
        ('6114', 'دعوى شهادة العمل', 'social', 'premiere_instance'),
        ('6115', 'دعوى التصريح بالعمال', 'social', 'premiere_instance'),
        ('6116', 'دعوى ساعات العمل الإضافية', 'social', 'premiere_instance'),
        ('6117', 'دعوى الترقية', 'social', 'premiere_instance'),
        ('6118', 'دعوى نقل تعسفي', 'social', 'premiere_instance'),
        ('6119', 'دعوى تحرش في العمل', 'social', 'premiere_instance'),
        ('6120', 'دعوى إعادة الإدماج', 'social', 'premiere_instance'),

        # === اجتماعي استئناف ===
        ('6201', 'استئناف حكم اجتماعي', 'social', 'appel'),
        ('6202', 'استئناف حكم حادثة شغل', 'social', 'appel'),
        ('6203', 'استئناف حكم ضمان اجتماعي', 'social', 'appel'),

        # === اجتماعي نقض ===
        ('6301', 'طعن بالنقض اجتماعي', 'social', 'cassation'),

        # === عقاري ابتدائي (Immobilier - Première instance) ===
        ('7101', 'دعوى عقارية', 'immobilier', 'premiere_instance'),
        ('7102', 'دعوى تحفيظ عقاري', 'immobilier', 'premiere_instance'),
        ('7103', 'تعرض على مطلب تحفيظ', 'immobilier', 'premiere_instance'),
        ('7104', 'دعوى تقييد بالرسم العقاري', 'immobilier', 'premiere_instance'),
        ('7105', 'دعوى تشطيب', 'immobilier', 'premiere_instance'),
        ('7106', 'دعوى استحقاق عقاري', 'immobilier', 'premiere_instance'),
        ('7107', 'دعوى قسمة عقارية', 'immobilier', 'premiere_instance'),
        ('7108', 'دعوى حدود عقار', 'immobilier', 'premiere_instance'),
        ('7109', 'دعوى ارتفاق عقاري', 'immobilier', 'premiere_instance'),
        ('7110', 'دعوى شفعة عقارية', 'immobilier', 'premiere_instance'),
        ('7111', 'دعوى الملكية المشتركة', 'immobilier', 'premiere_instance'),
        ('7112', 'دعوى بيع عقار مشاع', 'immobilier', 'premiere_instance'),
        ('7113', 'دعوى إفراغ عقار محفظ', 'immobilier', 'premiere_instance'),
        ('7114', 'دعوى التعرض على إيداع', 'immobilier', 'premiere_instance'),
        ('7115', 'دعوى تصحيح رسم عقاري', 'immobilier', 'premiere_instance'),
        ('7116', 'دعوى الأراضي السلالية', 'immobilier', 'premiere_instance'),
        ('7117', 'دعوى أراضي الجموع', 'immobilier', 'premiere_instance'),
        ('7118', 'دعوى أراضي الحبوس', 'immobilier', 'premiere_instance'),
        ('7119', 'دعوى الملك الغابوي', 'immobilier', 'premiere_instance'),
        ('7120', 'دعوى بطلان تقييد عقاري', 'immobilier', 'premiere_instance'),

        # === عقاري استئناف ===
        ('7201', 'استئناف حكم عقاري', 'immobilier', 'appel'),
        ('7202', 'استئناف حكم تحفيظ', 'immobilier', 'appel'),
        ('7203', 'استئناف حكم تعرض', 'immobilier', 'appel'),

        # === عقاري نقض ===
        ('7301', 'طعن بالنقض عقاري', 'immobilier', 'cassation'),

        # === تنفيذ (Exécution) ===
        ('8101', 'تنفيذ حكم مدني', 'execution', 'execution'),
        ('8102', 'تنفيذ حكم تجاري', 'execution', 'execution'),
        ('8103', 'تنفيذ حكم أسري', 'execution', 'execution'),
        ('8104', 'تنفيذ حكم اجتماعي', 'execution', 'execution'),
        ('8105', 'تنفيذ حكم إداري', 'execution', 'execution'),
        ('8106', 'تنفيذ أمر بالأداء', 'execution', 'execution'),
        ('8107', 'تنفيذ حكم أجنبي', 'execution', 'execution'),
        ('8108', 'حجز تنفيذي', 'execution', 'execution'),
        ('8109', 'حجز تحفظي', 'execution', 'execution'),
        ('8110', 'حجز لدى الغير', 'execution', 'execution'),
        ('8111', 'حجز عقاري', 'execution', 'execution'),
        ('8112', 'حجز منقولات', 'execution', 'execution'),
        ('8113', 'بيع بالمزاد العلني', 'execution', 'execution'),
        ('8114', 'إكراه بدني', 'execution', 'execution'),
        ('8115', 'صعوبة في التنفيذ', 'execution', 'execution'),
        ('8116', 'استحقاق فرعي', 'execution', 'execution'),
        ('8117', 'رفع حجز', 'execution', 'execution'),
        ('8118', 'تنفيذ حكم جنحي', 'execution', 'execution'),
        ('8119', 'تنفيذ عقد موثق', 'execution', 'execution'),
        ('8120', 'تنفيذ حكم تحكيمي', 'execution', 'execution'),

        # === تبليغ (Notification) ===
        ('9101', 'تبليغ حكم', 'notification', 'notification'),
        ('9102', 'تبليغ إنذار', 'notification', 'notification'),
        ('9103', 'تبليغ استدعاء', 'notification', 'notification'),
        ('9104', 'تبليغ قرار', 'notification', 'notification'),
        ('9105', 'تبليغ محضر', 'notification', 'notification'),
        ('9106', 'معاينة', 'notification', 'notification'),
        ('9107', 'استجواب', 'notification', 'notification'),
        ('9108', 'إثبات حال', 'notification', 'notification'),
        ('9109', 'عرض عيني وإيداع', 'notification', 'notification'),
        ('9110', 'احتجاج عدم الأداء', 'notification', 'notification'),

        # === قضاء القرب (Proximité) ===
        ('10101', 'دعوى قرب مدنية', 'proximite', 'premiere_instance'),
        ('10102', 'دعوى قرب جنحية', 'proximite', 'premiere_instance'),
        ('10103', 'مخالفة مرور', 'proximite', 'premiere_instance'),
        ('10104', 'نزاع جوار', 'proximite', 'premiere_instance'),
        ('10105', 'منقولات بسيطة', 'proximite', 'premiere_instance'),
        ('10106', 'ديون بسيطة', 'proximite', 'premiere_instance'),
        ('10107', 'إتلاف بسيط', 'proximite', 'premiere_instance'),
        ('10108', 'سب وقذف بسيط', 'proximite', 'premiere_instance'),
        ('10109', 'ضرب بسيط', 'proximite', 'premiere_instance'),
        ('10110', 'خلاف بين الجيران', 'proximite', 'premiere_instance'),

        # === شكاية (Plainte) ===
        ('11101', 'شكاية مباشرة', 'plainte', 'premiere_instance'),
        ('11102', 'شكاية لدى النيابة العامة', 'plainte', 'premiere_instance'),
        ('11103', 'شكاية لدى الشرطة القضائية', 'plainte', 'premiere_instance'),
        ('11104', 'شكاية مع التنصب كطرف مدني', 'plainte', 'premiere_instance'),
        ('11105', 'شكاية لدى قاضي التحقيق', 'plainte', 'premiere_instance'),
    ]

    objs = [
        CodeCategorieAffaire(code=c, libelle=l, domaine=d, niveau=n)
        for c, l, d, n in codes
    ]
    CodeCategorieAffaire.objects.bulk_create(objs, ignore_conflicts=True)


def reverse_seed(apps, schema_editor):
    CodeCategorieAffaire = apps.get_model('avocat_app', 'CodeCategorieAffaire')
    CodeCategorieAffaire.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('avocat_app', '0015_seed_moroccan_workflow_data'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeCategorieAffaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='أُنشئ في')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='تم التحديث في')),
                ('is_deleted', models.BooleanField(db_index=True, default=False, verbose_name='محذوف؟')),
                ('code', models.CharField(max_length=10, unique=True, verbose_name='الرمز')),
                ('libelle', models.CharField(max_length=200, verbose_name='التسمية')),
                ('domaine', models.CharField(choices=[
                    ('civil', 'مدني'), ('penal', 'جنائي'), ('famille', 'أسرة'),
                    ('commercial', 'تجاري'), ('administratif', 'إداري'),
                    ('social', 'اجتماعي'), ('immobilier', 'عقاري'),
                    ('execution', 'تنفيذ'), ('notification', 'تبليغ'),
                    ('proximite', 'قضاء القرب'), ('plainte', 'شكاية'),
                ], max_length=30, verbose_name='المجال')),
                ('niveau', models.CharField(choices=[
                    ('premiere_instance', 'ابتدائي'), ('appel', 'استئناف'),
                    ('cassation', 'نقض'), ('execution', 'تنفيذ'),
                    ('notification', 'تبليغ'),
                ], default='premiere_instance', max_length=20, verbose_name='الدرجة')),
            ],
            options={
                'verbose_name': 'رمز صنف القضية',
                'verbose_name_plural': 'رموز أصناف القضايا',
                'db_table': 'code_categorie_affaire',
                'ordering': ['code'],
            },
        ),
        migrations.AddField(
            model_name='affaire',
            name='numero_dossier',
            field=models.CharField(blank=True, max_length=20, null=True, verbose_name='رقم الملف'),
        ),
        migrations.AddField(
            model_name='affaire',
            name='code_categorie',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    to='avocat_app.codecategorieaffaire', verbose_name='صنف القضية'),
        ),
        migrations.AddField(
            model_name='affaire',
            name='annee_dossier',
            field=models.CharField(blank=True, max_length=4, null=True, verbose_name='السنة'),
        ),
        migrations.RunPython(seed_codes, reverse_seed),
    ]
