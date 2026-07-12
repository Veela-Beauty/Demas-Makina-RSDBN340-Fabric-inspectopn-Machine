"""Lightweight i18n for BRL-305 Monitor — Arabic + English, RTL-aware."""

_EN = {
    "lang.english": "English",
    "lang.arabic": "العربية",

    "login.title": "Sign in to Prime Textile",
    "login.subtitle": "Log in with your account so your inspections are recorded under your name.",
    "login.url": "Prime Textile URL",
    "login.username": "Username or email",
    "login.password": "Password",
    "login.btn": "Sign in",
    "login.required": "Enter URL, username and password.",
    "login.signing_in": "Signing in...",
    "login.unreachable": "Cannot reach Prime Textile: {}",
    "login.signed_out": "Signed out. Sign in with the new inspector account.",

    "top.port": "Port",
    "top.refresh": "Refresh",
    "top.connect": "Connect",
    "top.disconnect": "Disconnect",
    "top.connected": "Connected: {}",
    "top.disconnected": "Disconnected",
    "top.select_port": "Select a COM port first.",
    "top.connect_fail": "Failed to connect to {}.",
    "top.switch_user": "Switch user",
    "top.about": "BRL-305 Monitor 1.0.0\nRS232 fabric inspection + Prime Textile tunnel\nTarget: Windows 7 x86",

    "dash.read_meters": "Read Meters (R)",
    "dash.read_weight": "Read Weight (T)",
    "dash.reset": "Reset (S)",
    "dash.length": "LENGTH  (METERS)",
    "dash.weight": "WEIGHT",
    "dash.reset_ok": "Meters reset.",
    "dash.reset_fail": "Reset not confirmed.",

    "err.read_count": "Read Count (W)",
    "err.fetch_all": "Fetch All",
    "err.count": "Errors: {}",
    "err.count_na": "Errors: -",
    "err.header": "   #     METER        DETAIL",

    "cfg.erpnext": "Prime Textile",
    "cfg.server_url": "Server URL",
    "cfg.deep_scan": "Deep scan (push defects)",
    "cfg.verify_tls": "Verify TLS certificate",
    "cfg.save": "Save",
    "cfg.saved": "Saved.",
    "cfg.preset_title": "Set Preset (U command)",
    "cfg.preset_btn": "Set Preset",
    "cfg.preset_enter": "Enter a value first.",
    "cfg.preset_sent": "Preset sent.",
    "cfg.preset_fail": "Failed to send preset.",
    "cfg.detail_sent": "Detail written.",
    "cfg.detail_fail": "Failed to write detail.",
    "cfg.log_title": "Serial log (last 100)",

    "erp.work_order": "Work Order",
    "erp.roll_no": "Roll No",
    "erp.load_roll": "Load Roll",
    "erp.job_card": "Job Card",
    "erp.item": "Item",
    "erp.shade": "Shade",
    "erp.planned_length": "Planned length",
    "erp.read_machine": "Read Machine",
    "erp.save": "Save to Prime Textile",
    "erp.finalize": "Confirm & Submit",
    "erp.reading": "Reading machine...",
    "erp.read_empty": "Machine read returned nothing.",
    "erp.read_summary": "Machine: {} m  |  {} kg  |  {} defects",
    "erp.not_signed_in": "Not signed in.",
    "erp.load_first": "Load a roll first.",
    "erp.classify_title": "Classify defects",
    "erp.classify_msg": "{} machine defects have no Fabric Defect Type yet; map them in the Config tab, then Save again.",
    "erp.queued_save": "Queued save for {} ({} defects).",
    "erp.queued_finalize": "Queued Confirm & Submit for {}.",
    "erp.queue_idle": "Queue: idle",
    "erp.queue_status": "Queue: {}",
    "erp.no_machine": "Connect to the machine (top bar) first.",
    "erp.loaded": "Loaded {} - {} defect types available.",
    "erp.item_unknown": "?",
    "erp.shade_none": "-",
    "erp.length_unknown": "{} m",
    "erp.meter_row": "  {:>7}  m   {}",

    "web.title": "Prime Textile Portal",
    "web.subtitle": "Open the full Prime Textile system inside this app.",
    "web.open_portal": "Open Prime Textile",
    "web.open_inspection": "Open Inspection Page",
    "web.opening": "Opening Prime Textile...",
    "web.no_url": "Sign in first so the app knows your Prime Textile address.",
    "web.unavailable": "The in-app browser needs the WebView2 runtime. Opening in your default browser instead.",
    "web.hint": "Opens the Prime Textile web system inside this window. If it asks you to sign in, do it once — this machine remembers it. The native Inspection tab always works without a browser.",
}

_AR = {
    "lang.english": "English",
    "lang.arabic": "العربية",

    "login.title": "تسجيل الدخول إلى Prime Textile",
    "login.subtitle": "سجل الدخول بحسابك ليتم تسجيل عمليات الفحص باسمك.",
    "login.url": "رابط Prime Textile",
    "login.username": "اسم المستخدم أو البريد الإلكتروني",
    "login.password": "كلمة المرور",
    "login.btn": "تسجيل الدخول",
    "login.required": "الرجاء إدخال الرابط واسم المستخدم وكلمة المرور.",
    "login.signing_in": "جاري تسجيل الدخول...",
    "login.unreachable": "لا يمكن الوصول إلى Prime Textile: {}",
    "login.signed_out": "تم تسجيل الخروج. سجل الدخول بحساب المفتش الجديد.",

    "top.port": "المنفذ",
    "top.refresh": "تحديث",
    "top.connect": "اتصال",
    "top.disconnect": "قطع الاتصال",
    "top.connected": "متصل: {}",
    "top.disconnected": "غير متصل",
    "top.select_port": "الرجاء اختيار منفذ COM أولاً.",
    "top.connect_fail": "فشل الاتصال بـ {}.",
    "top.switch_user": "تغيير المستخدم",
    "top.about": "BRL-305 Monitor 1.0.0\nفحص القماش RS232 + نفق Prime Textile\nالهدف: Windows 7 x86",

    "dash.read_meters": "قراءة الطول (R)",
    "dash.read_weight": "قراءة الوزن (T)",
    "dash.reset": "إعادة ضبط (S)",
    "dash.length": "الطول (متر)",
    "dash.weight": "الوزن",
    "dash.reset_ok": "تم إعادة ضبط العداد.",
    "dash.reset_fail": "لم يتم تأكيد إعادة الضبط.",

    "err.read_count": "قراءة العدد (W)",
    "err.fetch_all": "جلب الكل",
    "err.count": "الأخطاء: {}",
    "err.count_na": "الأخطاء: -",
    "err.header": "   #     العداد        التفاصيل",

    "cfg.erpnext": "Prime Textile",
    "cfg.server_url": "رابط الخادم",
    "cfg.deep_scan": "فحص عميق (إرسال العيوب)",
    "cfg.verify_tls": "التحقق من شهادة TLS",
    "cfg.save": "حفظ",
    "cfg.saved": "تم الحفظ.",
    "cfg.preset_title": "تعيين القيمة المسبقة (أمر U)",
    "cfg.preset_btn": "تعيين",
    "cfg.preset_enter": "الرجاء إدخال قيمة أولاً.",
    "cfg.preset_sent": "تم إرسال القيمة المسبقة.",
    "cfg.preset_fail": "فشل إرسال القيمة المسبقة.",
    "cfg.detail_sent": "تم كتابة التفاصيل.",
    "cfg.detail_fail": "فشل كتابة التفاصيل.",
    "cfg.log_title": "سجل المنفذ التسلسلي (آخر 100)",

    "erp.work_order": "أمر العمل",
    "erp.roll_no": "رقم اللفة",
    "erp.load_roll": "تحميل اللفة",
    "erp.job_card": "بطاقة العمل",
    "erp.item": "الصنف",
    "erp.shade": "الدرجة",
    "erp.planned_length": "الطول المخطط",
    "erp.read_machine": "قراءة الآلة",
    "erp.save": "حفظ إلى Prime Textile",
    "erp.finalize": "تأكيد وإرسال",
    "erp.reading": "جاري قراءة الآلة...",
    "erp.read_empty": "لم يُرجع الجهاز أي شيء.",
    "erp.read_summary": "الآلة: {} م  |  {} كجم  |  {} عيوب",
    "erp.not_signed_in": "غير مسجل الدخول.",
    "erp.load_first": "الرجاء تحميل لفة أولاً.",
    "erp.classify_title": "تصنيف العيوب",
    "erp.classify_msg": "{} عيباً ليس لها نوع عيب قماشي محدد؛ قم بتعيينها في علامة التبويب الإعدادات، ثم احفظ مرة أخرى.",
    "erp.queued_save": "تمت جدولة الحفظ لـ {} ({} عيوب).",
    "erp.queued_finalize": "تمت جدولة التأكيد والإرسال لـ {}.",
    "erp.queue_idle": "قائمة الانتظار: خاملة",
    "erp.queue_status": "قائمة الانتظار: {}",
    "erp.no_machine": "الرجاء الاتصال بالآلة (الشريط العلوي) أولاً.",
    "erp.loaded": "تم التحميل {} - {} نوع عيب متاح.",
    "erp.item_unknown": "؟",
    "erp.shade_none": "-",
    "erp.length_unknown": "{} م",
    "erp.meter_row": "  {:>7}  م   {}",

    "web.title": "بوابة Prime Textile",
    "web.subtitle": "افتح نظام Prime Textile الكامل داخل هذا التطبيق.",
    "web.open_portal": "فتح Prime Textile",
    "web.open_inspection": "فتح صفحة الفحص",
    "web.opening": "جاري فتح Prime Textile...",
    "web.no_url": "سجّل الدخول أولاً ليعرف التطبيق عنوان Prime Textile.",
    "web.unavailable": "المتصفح المدمج يحتاج WebView2. سيتم الفتح في متصفحك الافتراضي بدلاً من ذلك.",
    "web.hint": "تعرض النافذة المدمجة نظام Prime Textile داخل هذا التطبيق. إذا طُلب تسجيل الدخول، سجّل مرة واحدة وسيتذكرها هذا الجهاز. تبويب الفحص المحلي يعمل دائماً بدون متصفح.",
}


class I18n:
    _lang = "en"

    @classmethod
    def set_lang(cls, lang):
        cls._lang = lang if lang in ("en", "ar") else "en"

    @classmethod
    def get(cls, key, *args, **kwargs):
        src = _AR if cls._lang == "ar" else _EN
        s = src.get(key, key)
        if args or kwargs:
            try:
                return s.format(*args, **kwargs)
            except (KeyError, IndexError):
                return s
        return s

    @classmethod
    def is_rtl(cls):
        return cls._lang == "ar"

    @classmethod
    def anchor(cls):
        return "e" if cls.is_rtl() else "w"

    @classmethod
    def justify(cls):
        return "right" if cls.is_rtl() else "left"

    @classmethod
    def lang_name(cls):
        return _EN.get("lang." + cls._lang, cls._lang)

    @classmethod
    def side(cls, s):
        if not cls.is_rtl():
            return s
        return {"left": "right", "right": "left"}.get(s, s)

    @classmethod
    def padx(cls, p):
        if not cls.is_rtl() or not isinstance(p, (tuple, list)) or len(p) != 2:
            return p
        return (p[1], p[0])

    @classmethod
    def grid_col(cls, col, total=2):
        if not cls.is_rtl():
            return col
        return total - 1 - col

    @classmethod
    def sticky(cls, s):
        if not cls.is_rtl():
            return s
        m = {"w": "e", "e": "w", "nw": "ne", "ne": "nw", "sw": "se",
             "se": "sw", "ew": "we", "we": "ew", "ns": "ns", "nesw": "nesw"}
        return m.get(s, s)


_ = I18n.get
