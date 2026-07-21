PHOTO_CATEGORIES = ["ac", "cleaning", "safety", "maintenance"]
NOTE_CATEGORIES = ["ac", "restrooms", "cleaning", "safety", "maintenance", "other"]

PHOTO_CATEGORY_LABELS = {
    "ac": "أعمال التكييف",
    "cleaning": "أعمال النظافة",
    "safety": "الأمن والسلامة",
    "maintenance": "أعمال الصيانة العامة",
}

NOTE_CATEGORY_LABELS = {
    "ac": "أعمال التكييف",
    "restrooms": "صيانة دورات المياه",
    "cleaning": "أعمال النظافة",
    "safety": "الأمن والسلامة",
    "maintenance": "الصيانة العامة",
    "other": "أخرى",
}

# slide index (0-based) in template.pptx for each category
PHOTO_SLIDE_INDEX = {"ac": 1, "cleaning": 2, "safety": 3, "maintenance": 4}
NOTE_SLIDE_INDEX = {
    "ac": 5,
    "restrooms": 6,
    "cleaning": 7,
    "safety": 8,
    "maintenance": 9,
    "other": 10,
}
COVER_SLIDE_INDEX = 0
MAX_PHOTOS_PER_CATEGORY = 10

DEFAULT_CHECKLIST_ITEMS = {
    "ac": ["صيانة الفلتر", "تعبئة الفريون", "جودة التبريد"],
    "restrooms": ["نظافة المغاسل", "سلامة الأدوات الصحية", "صيانة قفل الباب"],
    "cleaning": ["نظافة الممرات", "نظافة الفصول", "نظافة دورات المياه"],
    "safety": ["صلاحية طفايات الحريق", "سلامة مخارج الطوارئ", "لوحات الإرشاد"],
    "maintenance": ["صيانة الأبواب والنوافذ", "صيانة الدهانات", "صيانة الأسقف"],
    "other": [],
}
