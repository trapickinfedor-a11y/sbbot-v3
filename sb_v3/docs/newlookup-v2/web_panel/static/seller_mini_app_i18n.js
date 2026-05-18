'use strict';

/* ─────────────────────────────────────────────
   Seller Hub — i18n System (4 Languages)
   ───────────────────────────────────────────── */

const I18N = {
  en: {
    // Navigation
    nav_chats: 'Chats',
    nav_orders: 'Orders',
    nav_uploads: 'Uploads',
    nav_stats: 'Stats',
    nav_finance: 'Finance',
    nav_more: 'More',
    
    // Upload tabs
    upload_bank: '🏦 Bank',
    upload_brute: '⚡ Brute',
    upload_cc: '💳 CC',
    upload_nfc: '📱 NFC',
    upload_otp: '📲 OTP',
    upload_enroll: '🏦 Enroll',
    upload_selfreg_cc: '💳 Selfreg CC',
    upload_checks: '📄 Checks',
    upload_batches: '📋 Batches',
    upload_listings: '📃 Listings',
    
    // Common
    loading: 'Loading…',
    no_data: 'No data yet.',
    select_item: 'Select an item',
    save: 'Save',
    cancel: 'Cancel',
    submit: 'Submit',
    preview: 'Preview',
    delete: 'Delete',
    edit: 'Edit',
    back: 'Back',
    
    // Status
    status_approved: 'Approved',
    status_pending: 'Pending',
    status_rejected: 'Rejected',
    status_active: 'Active',
    status_inactive: 'Inactive',
    
    // Finance
    finance_balance: 'Balance',
    finance_pending: 'Pending',
    finance_withdraw: 'Withdraw',
    finance_deposit: 'Deposit',
    
    // CC Upload
    cc_product_type: 'Product Type',
    cc_category: 'Category',
    cc_number: 'Card Number',
    cc_exp: 'Expiration',
    cc_cvv: 'CVV',
    cc_non_vbv: 'NON-VBV',
    cc_extra_data: 'Extra Data',
    cc_phone: 'Phone',
    cc_email: 'Email',
    cc_ssn: 'SSN',
    cc_dl: 'Driver License',
    cc_bulk_format: 'Bulk Format',
    
    // NFC Upload
    nfc_type: 'NFC Type',
    nfc_apple_pay: 'Apple Pay',
    nfc_google_pay: 'Google Pay',
    nfc_other: 'Other',
    
    // OTP Upload
    otp_balance: 'Balance',
    otp_sms_access: 'SMS Access',
    
    // Enroll Upload
    enroll_portal: 'Portal',
    enroll_card_type: 'Card Type',
    enroll_state: 'State',
    enroll_zip: 'ZIP',
    
    // Checks Upload
    checks_type: 'Check Type',
    checks_personal: 'Personal',
    checks_business: 'Business',
    checks_payroll: 'Payroll',
    checks_cashier: 'Cashier',
    checks_amount: 'Amount',
    checks_date: 'Date',
    
    // Batches & Listings
    batches_title: 'Your Batches',
    batches_detail: 'Batch Details',
    listings_title: 'Active Listings',
    listings_bulk_reprice: 'Bulk Reprice',
    listings_templates: 'Saved Templates',
    
    // Settings
    settings_language: 'Language',
    settings_vacation: 'Vacation Mode',
    settings_notifications: 'Notifications',
  },
  
  ru: {
    // Navigation
    nav_chats: 'Чаты',
    nav_orders: 'Заказы',
    nav_uploads: 'Загрузки',
    nav_stats: 'Статистика',
    nav_finance: 'Финансы',
    nav_more: 'Ещё',
    
    // Upload tabs
    upload_bank: '🏦 Банк',
    upload_brute: '⚡ Brute',
    upload_cc: '💳 Карты',
    upload_nfc: '📱 NFC',
    upload_otp: '📲 OTP',
    upload_enroll: '🏦 Enroll',
    upload_selfreg_cc: '💳 Selfreg CC',
    upload_checks: '📄 Чеки',
    upload_batches: '📋 Пакеты',
    upload_listings: '📃 Товары',
    
    // Common
    loading: 'Загрузка…',
    no_data: 'Пока нет данных.',
    select_item: 'Выберите элемент',
    save: 'Сохранить',
    cancel: 'Отмена',
    submit: 'Отправить',
    preview: 'Предпросмотр',
    delete: 'Удалить',
    edit: 'Изменить',
    back: 'Назад',
    
    // Status
    status_approved: 'Одобрено',
    status_pending: 'На проверке',
    status_rejected: 'Отклонено',
    status_active: 'Активно',
    status_inactive: 'Неактивно',
    
    // Finance
    finance_balance: 'Баланс',
    finance_pending: 'В ожидании',
    finance_withdraw: 'Вывод',
    finance_deposit: 'Депозит',
    
    // CC Upload
    cc_product_type: 'Тип продукта',
    cc_category: 'Категория',
    cc_number: 'Номер карты',
    cc_exp: 'Срок действия',
    cc_cvv: 'CVV',
    cc_non_vbv: 'NON-VBV',
    cc_extra_data: 'Доп. данные',
    cc_phone: 'Телефон',
    cc_email: 'Email',
    cc_ssn: 'SSN',
    cc_dl: 'Водительские права',
    cc_bulk_format: 'Массовая загрузка',
    
    // NFC Upload
    nfc_type: 'Тип NFC',
    nfc_apple_pay: 'Apple Pay',
    nfc_google_pay: 'Google Pay',
    nfc_other: 'Другое',
    
    // OTP Upload
    otp_balance: 'Баланс',
    otp_sms_access: 'SMS доступ',
    
    // Enroll Upload
    enroll_portal: 'Портал',
    enroll_card_type: 'Тип карты',
    enroll_state: 'Штат',
    enroll_zip: 'Индекс',
    
    // Checks Upload
    checks_type: 'Тип чека',
    checks_personal: 'Личный',
    checks_business: 'Бизнес',
    checks_payroll: 'Зарплатный',
    checks_cashier: 'Кассирский',
    checks_amount: 'Сумма',
    checks_date: 'Дата',
    
    // Batches & Listings
    batches_title: 'Ваши пакеты',
    batches_detail: 'Детали пакета',
    listings_title: 'Активные товары',
    listings_bulk_reprice: 'Массовое изменение цен',
    listings_templates: 'Сохраненные шаблоны',
    
    // Settings
    settings_language: 'Язык',
    settings_vacation: 'Режим отпуска',
    settings_notifications: 'Уведомления',
  },
  
  zh: {
    // Navigation
    nav_chats: '聊天',
    nav_orders: '订单',
    nav_uploads: '上传',
    nav_stats: '统计',
    nav_finance: '财务',
    nav_more: '更多',
    
    // Upload tabs
    upload_bank: '🏦 银行',
    upload_brute '⚡ Brute',
    upload_cc: '💳 信用卡',
    upload_nfc: '📱 NFC',
    upload_otp: '📲 OTP',
    upload_enroll: '🏦 Enroll',
    upload_selfreg_cc: '💳 Selfreg CC',
    upload_checks: '📄 支票',
    upload_batches: '📋 批次',
    upload_listings: '📃 商品',
    
    // Common
    loading: '加载中…',
    no_data: '暂无数据',
    select_item: '选择项目',
    save: '保存',
    cancel: '取消',
    submit: '提交',
    preview: '预览',
    delete: '删除',
    edit: '编辑',
    back: '返回',
    
    // Status
    status_approved: '已批准',
    status_pending: '待审核',
    status_rejected: '已拒绝',
    status_active: '活跃',
    status_inactive: '未激活',
    
    // Finance
    finance_balance: '余额',
    finance_pending: '待处理',
    finance_withdraw: '提现',
    finance_deposit: '存款',
    
    // CC Upload
    cc_product_type: '产品类型',
    cc_category: '类别',
    cc_number: '卡号',
    cc_exp: '有效期',
    cc_cvv: 'CVV',
    cc_non_vbv: 'NON-VBV',
    cc_extra_data: '额外数据',
    cc_phone: '电话',
    cc_email: '邮箱',
    cc_ssn: 'SSN',
    cc_dl: '驾驶执照',
    cc_bulk_format: '批量格式',
    
    // NFC Upload
    nfc_type: 'NFC 类型',
    nfc_apple_pay: 'Apple Pay',
    nfc_google_pay: 'Google Pay',
    nfc_other: '其他',
    
    // OTP Upload
    otp_balance: '余额',
    otp_sms_access: '短信访问',
    
    // Enroll Upload
    enroll_portal: '门户',
    enroll_card_type: '卡类型',
    enroll_state: '州',
    enroll_zip: '邮编',
    
    // Checks Upload
    checks_type: '支票类型',
    checks_personal: '个人',
    checks_business: '商业',
    checks_payroll: '工资',
    checks_cashier: '银行',
    checks_amount: '金额',
    checks_date: '日期',
    
    // Batches & Listings
    batches_title: '您的批次',
    batches_detail: '批次详情',
    listings_title: '活跃商品',
    listings_bulk_reprice: '批量改价',
    listings_templates: '保存的模板',
    
    // Settings
    settings_language: '语言',
    settings_vacation: '休假模式',
    settings_notifications: '通知',
  },
  
  es: {
    // Navigation
    nav_chats: 'Chats',
    nav_orders: 'Pedidos',
    nav_uploads: 'Subidas',
    nav_stats: 'Estadísticas',
    nav_finance: 'Finanzas',
    nav_more: 'Más',
    
    // Upload tabs
    upload_bank: '🏦 Banco',
    upload_brute: '⚡ Brute',
    upload_cc: '💳 Tarjeta',
    upload_nfc: '📱 NFC',
    upload_otp: '📲 OTP',
    upload_enroll: '🏦 Enroll',
    upload_selfreg_cc: '💳 Selfreg CC',
    upload_checks: '📄 Cheques',
    upload_batches: '📋 Lotes',
    upload_listings: '📃 Listados',
    
    // Common
    loading: 'Cargando…',
    no_data: 'Sin datos aún.',
    select_item: 'Seleccionar elemento',
    save: 'Guardar',
    cancel: 'Cancelar',
    submit: 'Enviar',
    preview: 'Vista previa',
    delete: 'Eliminar',
    edit: 'Editar',
    back: 'Atrás',
    
    // Status
    status_approved: 'Aprobado',
    status_pending: 'Pendiente',
    status_rejected: 'Rechazado',
    status_active: 'Activo',
    status_inactive: 'Inactivo',
    
    // Finance
    finance_balance: 'Saldo',
    finance_pending: 'Pendiente',
    finance_withdraw: 'Retirar',
    finance_deposit: 'Depósito',
    
    // CC Upload
    cc_product_type: 'Tipo de producto',
    cc_category: 'Categoría',
    cc_number: 'Número de tarjeta',
    cc_exp: 'Vencimiento',
    cc_cvv: 'CVV',
    cc_non_vbv: 'NON-VBV',
    cc_extra_data: 'Datos extra',
    cc_phone: 'Teléfono',
    cc_email: 'Email',
    cc_ssn: 'SSN',
    cc_dl: 'Licencia de conducir',
    cc_bulk_format: 'Formato masivo',
    
    // NFC Upload
    nfc_type: 'Tipo NFC',
    nfc_apple_pay: 'Apple Pay',
    nfc_google_pay: 'Google Pay',
    nfc_other: 'Otro',
    
    // OTP Upload
    otp_balance: 'Saldo',
    otp_sms_access: 'Acceso SMS',
    
    // Enroll Upload
    enroll_portal: 'Portal',
    enroll_card_type: 'Tipo de tarjeta',
    enroll_state: 'Estado',
    enroll_zip: 'Código postal',
    
    // Checks Upload
    checks_type: 'Tipo de cheque',
    checks_personal: 'Personal',
    checks_business: 'Negocios',
    checks_payroll: 'Nómina',
    checks_cashier: 'Cajero',
    checks_amount: 'Monto',
    checks_date: 'Fecha',
    
    // Batches & Listings
    batches_title: 'Sus lotes',
    batches_detail: 'Detalles del lote',
    listings_title: 'Listados activos',
    listings_bulk_reprice: 'Recotización masiva',
    listings_templates: 'Plantillas guardadas',
    
    // Settings
    settings_language: 'Idioma',
    settings_vacation: 'Modo vacaciones',
    settings_notifications: 'Notificaciones',
  },
};

// Current language
let currentLang = 'en';

// Get translation
function t(key, lang = currentLang) {
  const keys = key.split('.');
  let value = I18N[lang];
  for (const k of keys) {
    if (value && typeof value === 'object') {
      value = value[k];
    } else {
      return key;
    }
  }
  return value || key;
}

// Set language
function setLanguage(lang) {
  if (!I18N[lang]) {
    console.warn(`Language '${lang}' not found, using 'en'`);
    lang = 'en';
  }
  currentLang = lang;
  localStorage.setItem('seller_mini_app_lang', lang);
  applyTranslations();
}

// Get saved language
function getSavedLanguage() {
  return localStorage.getItem('seller_mini_app_lang') || 'en';
}

// Apply translations to DOM
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const placeholder = el.getAttribute('data-i18n-placeholder');
    const title = el.getAttribute('data-i18n-title');
    
    if (key) {
      el.textContent = t(key);
    }
    if (placeholder) {
      el.placeholder = t(placeholder);
    }
    if (title) {
      el.title = t(title);
    }
  });
  
  // Update tab buttons
  document.querySelectorAll('.upload-tab').forEach(btn => {
    const key = btn.getAttribute('data-i18n-tab');
    if (key) {
      btn.textContent = t(key);
    }
  });
  
  // Dispatch event for dynamic content
  window.dispatchEvent(new CustomEvent('i18n:updated', { detail: { lang: currentLang } }));
}

// Initialize i18n
function initI18n() {
  const savedLang = getSavedLanguage();
  setLanguage(savedLang);
}

// Export for use in main JS
window.I18N = I18N;
window.t = t;
window.setLanguage = setLanguage;
window.getSavedLanguage = getSavedLanguage;
window.initI18n = initI18n;
