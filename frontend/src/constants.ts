export const PHOTO_CATEGORIES = ['ac', 'cleaning', 'safety', 'maintenance'] as const
export const NOTE_CATEGORIES = ['ac', 'restrooms', 'cleaning', 'safety', 'maintenance', 'other'] as const

export const PHOTO_CATEGORY_LABELS: Record<string, string> = {
  ac: 'أعمال التكييف',
  cleaning: 'أعمال النظافة',
  safety: 'الأمن والسلامة',
  maintenance: 'أعمال الصيانة العامة',
}

export const NOTE_CATEGORY_LABELS: Record<string, string> = {
  ac: 'أعمال التكييف',
  restrooms: 'صيانة دورات المياه',
  cleaning: 'أعمال النظافة',
  safety: 'الأمن والسلامة',
  maintenance: 'الصيانة العامة',
  other: 'أخرى',
}

export const MAX_PHOTOS_PER_CATEGORY = 10

export const REVIEW_RESPONSE_OPTIONS = [
  'تمت المعالجة',
  'معالجة جزئية',
  'جاري التنفيذ',
  'لم تتم المعالجة',
] as const
