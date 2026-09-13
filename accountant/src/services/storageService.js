// Storage Service for CJS Accountant
// Dual layer: local storage cache + reactive subscribers + Google Sheets syncing

const STORAGE_KEYS = {
  CONFIG: 'cjs_config',
  SALES: 'cjs_sales_ledger',
  EXPENSES: 'cjs_expense_ledger',
  ASSETS: 'cjs_asset_ledger',
  CAPITAL: 'cjs_capital_ledger',
  CUSTOMERS: 'cjs_customers',
  VENDORS: 'cjs_vendors',
  ORDERS: 'cjs_ai_orders',
  DESCRIPTION_TEMPLATES: 'cjs_description_templates',
  SETTINGS: 'cjs_app_settings',
  PIN: 'cjs_app_pin',
  SYNC_META: 'cjs_sync_meta'
};

/**
 * Robustly parses numbers from Google Sheets formatted with currency symbols (₹, INR, Rs),
 * commas (Indian or International formatting: 1,20,000 or 1,200,000), spaces, or negative parentheses.
 */
export function parseCurrency(val) {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : val;
  let str = String(val).trim();
  if (!str) return 0;

  const isNegative = str.startsWith('-') || (str.startsWith('(') && str.endsWith(')'));
  // Remove currency identifiers: ₹, Rs, Rs., INR, $, €, £, etc.
  str = str.replace(/[₹$€£]|INR|Rs\.?|CAD|USD|EUR/gi, '');
  // Remove commas, quotes, parentheses, spaces, and non-breaking spaces
  str = str.replace(/[,()'"\s\u00A0]/g, '');

  const parsed = parseFloat(str);
  if (isNaN(parsed)) return 0;
  return isNegative ? -Math.abs(parsed) : parsed;
}

export function parseInteger(val) {
  if (val === null || val === undefined) return 0;
  if (typeof val === 'number') return isNaN(val) ? 0 : Math.round(val);
  const clean = parseCurrency(val);
  return Math.round(clean);
}

export function parseSheetDate(str) {
  if (!str) return null;
  if (str instanceof Date) return isNaN(str.getTime()) ? null : str;
  let s = String(str).trim();
  if (!s) return null;

  // Try standard Date constructor
  let d = new Date(s);
  if (!isNaN(d.getTime())) return d;

  // Match DD-Mon-YYYY or DD-Month-YYYY (e.g. 10-Mar-2023 or 10-March-2023)
  const monMatch = s.match(/^(\d{1,2})[-/ ]([A-Za-z]+)[-/ ](\d{2,4})$/);
  if (monMatch) {
    const monthMap = {
      jan: 0, january: 0,
      feb: 1, february: 1,
      mar: 2, march: 2,
      apr: 3, april: 3,
      may: 4,
      jun: 5, june: 5,
      jul: 6, july: 6,
      aug: 7, august: 7,
      sep: 8, sept: 8, september: 8,
      oct: 9, october: 9,
      nov: 10, november: 10,
      dec: 11, december: 11
    };
    const m = monthMap[monMatch[2].toLowerCase()];
    if (m !== undefined) {
      let yr = parseInt(monMatch[3], 10);
      if (yr < 100) yr += 2000;
      const day = parseInt(monMatch[1], 10);
      return new Date(yr, m, day);
    }
  }

  // Match DD/MM/YYYY or DD-MM-YYYY
  const dmyMatch = s.match(/^(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})$/);
  if (dmyMatch) {
    let yr = parseInt(dmyMatch[3], 10);
    if (yr < 100) yr += 2000;
    const day = parseInt(dmyMatch[1], 10);
    const m = parseInt(dmyMatch[2], 10) - 1;
    return new Date(yr, m, day);
  }

  return null;
}

// Seed Config
const DEFAULT_CONFIG = {
  stitch_rate_per_1000: 8,
  hourly_labor_rate: 100,
  gst_rate_percent: 18,
  studio_name: 'CJS Designs',
  tagline: 'Crafting fashion on fabric',
  studio_address: 'New Kerala Nagar, Peringala, Cochin, Kerala - 683565',
  studio_phone: '+91 8289897413',
  studio_email: 'cjstechnologies.in@gmail.com',
  studio_gstin: '32DXRPS1247C1ZG',
  bank_name: 'HDFC Bank Ltd',
  account_number: '50200012345678',
  ifsc_code: 'HDFC0001234',
  upi_id: ''
};

// Default App Settings
const DEFAULT_SETTINGS = {
  useGoogleSheets: true,
  googleSheetId: '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA',
  googleScriptUrl: '',
  syncIntervalMin: 5,
  currencySymbol: '₹',
  autoLockMinutes: 15,
  enableBiometrics: true
};

let memoryStore = {};
function getStorage() {
  if (typeof window !== 'undefined' && window.localStorage) {
    return window.localStorage;
  }
  return {
    getItem: (k) => memoryStore[k] || null,
    setItem: (k, v) => { memoryStore[k] = String(v); },
    removeItem: (k) => { delete memoryStore[k]; }
  };
}

class StorageService {
  constructor() {
    this.subscribers = new Set();
    this.init();
  }

  init() {
    const storage = getStorage();
    const storedConfig = this.get(STORAGE_KEYS.CONFIG);
    if (!storedConfig) {
      this.save(STORAGE_KEYS.CONFIG, DEFAULT_CONFIG);
    } else {
      let needsUpdate = false;
      const updates = {};
      if (storedConfig.studio_address?.includes('Fashion Craft Arcade') || storedConfig.studio_address?.includes('12/24')) {
        updates.studio_address = (storedConfig.studio_address || '').replace(/12\/24,?\s*/gi, '') || DEFAULT_CONFIG.studio_address;
        needsUpdate = true;
      }
      if (storedConfig.upi_id === 'cjsdesigns@hdfcbank') {
        updates.upi_id = '';
        needsUpdate = true;
      }
      if (storedConfig.studio_phone === '+91 98470 12345' || storedConfig.studio_phone?.includes('98470')) {
        updates.studio_phone = DEFAULT_CONFIG.studio_phone;
        needsUpdate = true;
      }
      if (storedConfig.studio_email === 'billing@cjsdesigns.in' || storedConfig.studio_email?.includes('billing@cjsdesigns.in')) {
        updates.studio_email = DEFAULT_CONFIG.studio_email;
        needsUpdate = true;
      }
      if (storedConfig.studio_gstin === '32ABCDE1234F1Z5') {
        updates.studio_gstin = DEFAULT_CONFIG.studio_gstin;
        needsUpdate = true;
      }
      if (needsUpdate) {
        this.updateConfig(updates);
      }
    }
    if (!storage.getItem(STORAGE_KEYS.SALES)) {
      this.save(STORAGE_KEYS.SALES, []);
    }
    if (!storage.getItem(STORAGE_KEYS.EXPENSES)) {
      this.save(STORAGE_KEYS.EXPENSES, []);
    }
    if (!storage.getItem(STORAGE_KEYS.ASSETS)) {
      this.save(STORAGE_KEYS.ASSETS, []);
    }
    if (!storage.getItem(STORAGE_KEYS.CAPITAL)) {
      this.save(STORAGE_KEYS.CAPITAL, []);
    }
    if (!storage.getItem(STORAGE_KEYS.CUSTOMERS)) {
      this.save(STORAGE_KEYS.CUSTOMERS, []);
    }
    if (!storage.getItem(STORAGE_KEYS.VENDORS)) {
      this.save(STORAGE_KEYS.VENDORS, []);
    }
    if (!storage.getItem(STORAGE_KEYS.ORDERS)) {
      this.save(STORAGE_KEYS.ORDERS, []);
    }
    if (!storage.getItem(STORAGE_KEYS.SETTINGS)) {
      this.save(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
    }
    if (!storage.getItem(STORAGE_KEYS.PIN) || storage.getItem(STORAGE_KEYS.PIN) === '1234') {
      storage.setItem(STORAGE_KEYS.PIN, '8911');
    }
  }

  hydrateFromSheets({ customers, vendors, sales, expenses, assets, capital, orders, descriptionTemplates }) {
    if (Array.isArray(customers) && customers.length > 0) {
      const mappedCust = customers.map(c => ({
        id: c['Customer ID'] || c.id || '',
        name: c['Name'] || c.name || '',
        phone: c['Phone'] || c.phone || '',
        address: c['Address'] || c.address || ''
      }));
      this.save(STORAGE_KEYS.CUSTOMERS, mappedCust);
    }

    if (Array.isArray(vendors) && vendors.length > 0) {
      const mappedVendors = vendors.map(v => ({
        id: v['Vendor ID'] || v.id || '',
        name: v['Name'] || v.name || '',
        category: v['Category'] || v.category || '',
        contactPerson: v['Contact Person'] || v.contactPerson || '',
        phone: v['Phone'] || v.phone || '',
        address: v['Address'] || v.address || ''
      }));
      this.save(STORAGE_KEYS.VENDORS, mappedVendors);
    }

    if (Array.isArray(sales) && sales.length > 0) {
      const mappedSales = sales.map(s => {
        const lHrs = parseCurrency(s['Labor Hrs'] || s.laborHours || 0);
        const lMins = s['Labor Minutes'] !== undefined ? parseInteger(s['Labor Minutes']) : (s.laborMinutes !== undefined ? parseInteger(s.laborMinutes) : Math.round(lHrs * 60));
        return {
          id: s['Invoice ID'] || s.id,
          date: s['Date'] || s.date,
          customer: s['Customer'] || s.customer,
          serviceType: s['Service Type'] || s.serviceType,
          totalStitches: parseInteger(s['Total Stitches'] || s.totalStitches || 0),
          laborHours: lHrs,
          laborMinutes: lMins,
          marginPercent: parseCurrency(s['Margin %'] || s.marginPercent || 0),
          netPrice: parseCurrency(s['Net Price'] || s.netPrice || 0),
          gst: parseCurrency(s['GST'] || s.gst || 0),
          courier: parseCurrency(s['Courier'] || s.courier || 0),
          grossTotal: parseCurrency(s['Gross Total'] || s.grossTotal || 0),
          status: s.status || 'Paid',
          imageUrl: s['Image URL'] || s.imageUrl || s.image_url || '',
          orderRef: s.orderRef || s['Order ID'] || s.orderId || null
        };
      });
      this.save(STORAGE_KEYS.SALES, mappedSales);
    }

    if (Array.isArray(expenses) && expenses.length > 0) {
      const mappedExpenses = expenses.map((e, idx) => ({
        id: e.id || `EXP-SHT-${idx + 1}`,
        date: e['Date'] || e.date,
        category: e['Expense Category'] || e.category,
        description: e['Description'] || e.description,
        amount: parseCurrency(e['Amount'] || e.amount || 0),
        paymentMethod: e['Payment Method'] || e.paymentMethod || 'UPI'
      }));
      this.save(STORAGE_KEYS.EXPENSES, mappedExpenses);
    }

    if (Array.isArray(assets) && assets.length > 0) {
      const mappedAssets = assets.map((a, idx) => {
        const purchasePrice = parseCurrency(a['Purchase Price'] || a.purchasePrice || 0);
        const usefulLifeMonths = parseInteger(a['Useful Life (Months)'] || a.usefulLifeMonths || 36);
        const monthlyDepreciation = parseCurrency(a['Monthly Depreciation'] || a.monthlyDepreciation || 0) || Number((purchasePrice / Math.max(1, usefulLifeMonths)).toFixed(2));
        return {
          id: a.id || `AST-SHT-${idx + 1}`,
          name: a['Asset Name'] || a.name,
          purchaseDate: a['Purchase Date'] || a.purchaseDate,
          purchasePrice,
          usefulLifeMonths,
          monthlyDepreciation,
          active: true
        };
      });
      this.save(STORAGE_KEYS.ASSETS, mappedAssets);
    }

    if (Array.isArray(capital) && capital.length > 0) {
      const mappedCapital = capital.map((c, idx) => ({
        id: c.id || `CAP-SHT-${idx + 1}`,
        date: c['Date'] || c.date,
        transactionType: c['Transaction Type'] || c.transactionType,
        description: c['Description'] || c.description,
        amount: parseCurrency(c['Amount'] || c.amount || 0)
      }));
      this.save(STORAGE_KEYS.CAPITAL, mappedCapital);
    }

    if (Array.isArray(orders) && orders.length > 0) {
      const mappedOrders = orders.map((o, idx) => {
        let stitchCount = 0;
        const rawStitch = o['Stitch Count'] || o.stitchCount || '';
        const reasoningText = o['Reasoning '] || o['Reasoning'] || o.reasoning || '';
        if (typeof rawStitch === 'string' && rawStitch.includes('-')) {
          // Date formatting anomaly in Google Sheets (e.g. 1918-02-03)
          const match = reasoningText.match(/(\d+)\s+total stitches/i) || reasoningText.match(/(\d+)\s*st\b/i);
          stitchCount = match ? parseInt(match[1], 10) : parseInteger(rawStitch);
        } else {
          stitchCount = parseInteger(rawStitch || 0);
          if (stitchCount === 0 && reasoningText) {
            const match = reasoningText.match(/(\d+)\s+total stitches/i) || reasoningText.match(/(\d+)\s*st\b/i);
            if (match) stitchCount = parseInt(match[1], 10);
          }
        }

        const orderType = o['Order Type'] || o['Embroidery Type'] || o.orderType || o.embroideryType || '';
        const lHrs = parseFloat(o['Labor Hours'] || o.laborHours || 0) || 0;
        const lMins = o['Labor Minutes'] !== undefined ? parseInteger(o['Labor Minutes']) : (o.laborMinutes !== undefined ? parseInteger(o.laborMinutes) : Math.round(lHrs * 60));

        return {
          id: o['Order ID'] || o.id || `ORD-${idx + 1}`,
          orderDate: o['Order Date'] || o.orderDate || '',
          customerId: o['Customer ID'] || o.customerId || '',
          customerName: o['Customer Name'] || o.customerName || '',
          phone: o['Phone'] || o.phone || '',
          orderType: orderType,
          templateName: o['Template Name'] || o.templateName || '',
          quantity: parseInteger(o['Quantity'] || o.quantity || 1) || 1,
          laborHours: lHrs,
          laborMinutes: lMins,
          material: o['Material'] || o.material || '',
          embroideryType: orderType,
          stitchCount,
          machine: o['Machine'] || o.machine || '',
          estimatedDeliveryDate: o['Estimated Delivery Date'] || o.estimatedDeliveryDate || '',
          estimatedCost: o['Estimated Cost'] || o.estimatedCost || '',
          status: o['Payment Status'] || o.status || 'Estimated',
          reasoning: reasoningText,
          overrides: o['Overrides'] || o.overrides || '',
          overrideDeliveryDate: o['Override Delivery Date'] || o.overrideDeliveryDate || '',
          overrideCost: o['Override Cost (Rs)'] || o.overrideCost || '',
          overrideMachine: o['Override Machine'] || o.overrideMachine || '',
          imageUrl: o['Image URL'] || o.imageUrl || o.image_url || ''
        };
      });
      this.save(STORAGE_KEYS.ORDERS, mappedOrders);
    }

    if (Array.isArray(descriptionTemplates) && descriptionTemplates.length > 0) {
      const mappedTemplates = descriptionTemplates.map((t, idx) => {
        const serviceCategory = t['Service Category'] || t['Service category'] || t['Category'] || t.category || t.serviceCategory || 'Machine Embroidery';
        const description = t['Description'] || t['description'] || '';
        const name = t['Template Name'] || t['templateName'] || t.name || '';
        const machine = t['Machine'] || t.machine || '';
        const laborMinutes = parseInteger(t['Labor Minutes'] || t.laborMinutes || 0);
        const stitchCount = parseInteger(t['Stitch Count'] || t.stitchCount || 0);

        return {
          id: `TPL-${idx + 1}`,
          serviceCategory: serviceCategory.trim(),
          description: description.trim(),
          name: name.trim(),
          machine: machine.trim(),
          laborMinutes,
          stitchCount
        };
      }).filter(t => Boolean(t.description));
      this.save(STORAGE_KEYS.DESCRIPTION_TEMPLATES, mappedTemplates);
    }

    this.notify('HYDRATE_FROM_SHEETS');
  }

  getCustomers() {
    return this.get(STORAGE_KEYS.CUSTOMERS, []);
  }

  getDescriptionTemplates() {
    const fallbackPresets = [
      { serviceCategory: 'Machine Embroidery', name: 'Blouse Back & Sleeves', description: 'Gold Zari Floral Blouse Back & Sleeves Embroidery' },
      { serviceCategory: 'Machine Embroidery', name: 'Silk Dupatta Work', description: 'Tussar Silk Dupatta All-Over Mirror & Threadwork' },
      { serviceCategory: 'Machine Embroidery', name: 'Velvet Gown Yoke', description: 'Velvet Gown Yoke Embroidery with Metallic Cording' },
      { serviceCategory: 'Machine Embroidery', name: 'Peacock Zari Motif', description: 'Traditional Peacock Zari Motif on Silk Fabric' },
      { serviceCategory: 'Machine Embroidery', name: 'Floral Border Work', description: 'Multi-Color Floral Embroidery Running Border Work' },
      { serviceCategory: 'Bridal Embroidery', name: 'Bridal Lehenga Motif', description: 'Bridal Lehenga Custom Resham & Zari Motif Work' },
      { serviceCategory: 'Bridal Embroidery', name: 'Bridal Saree Border', description: 'Heavy Bridal Saree Border & Pallu Cutwork Embroidery' },
      { serviceCategory: 'Kurti & Salwar', name: 'Kurti Neck & Cuffs', description: 'Kurti Neckline & Sleeve Cuffs Multi-Thread Work' },
      { serviceCategory: 'Machine Embroidery Design Making', name: 'Master Digitizing', description: 'DST & EMB Master Digitizing for Crest / Logo' },
      { serviceCategory: 'Uniform & Corporate', name: 'Corporate Crest', description: 'Corporate Polo Crest Monogram & Badge Embroidery' },
      { serviceCategory: 'Garment Alteration / Rework', name: 'Patch & Border Rework', description: 'Embroidery Patch Application & Border Replacement' }
    ];
    return this.get(STORAGE_KEYS.DESCRIPTION_TEMPLATES, fallbackPresets);
  }

  getServiceCategories() {
    const templates = this.getDescriptionTemplates();
    const categories = Array.from(new Set(templates.map(t => t.serviceCategory).filter(Boolean)));
    if (categories.length === 0) {
      return [
        'Machine Embroidery',
        'Bridal Embroidery',
        'Kurti & Salwar',
        'Machine Embroidery Design Making',
        'Uniform & Corporate',
        'Garment Alteration / Rework'
      ];
    }
    return categories;
  }

  addCustomer(customer) {
    const customers = this.getCustomers();
    if (!customers.some(c => c.name.toLowerCase() === customer.name.toLowerCase())) {
      customers.push(customer);
      this.save(STORAGE_KEYS.CUSTOMERS, customers);
    }
    return customer;
  }

  getVendors() {
    return this.get(STORAGE_KEYS.VENDORS, []);
  }

  addVendor(vendor) {
    const vendors = this.getVendors();
    if (!vendors.some(v => v.name.toLowerCase() === vendor.name.toLowerCase())) {
      vendors.push(vendor);
      this.save(STORAGE_KEYS.VENDORS, vendors);
    }
    return vendor;
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify(event, data) {
    for (const callback of this.subscribers) {
      try {
        callback(event, data);
      } catch (err) {
        console.error('Storage subscriber error:', err);
      }
    }
  }

  get(key, fallback = null) {
    try {
      const storage = getStorage();
      const data = storage.getItem(key);
      return data ? JSON.parse(data) : fallback;
    } catch (e) {
      console.error('Error reading localStorage key:', key, e);
      return fallback;
    }
  }

  save(key, data) {
    try {
      const storage = getStorage();
      storage.setItem(key, JSON.stringify(data));
      this.notify(key, data);
      return true;
    } catch (e) {
      console.error('Error writing to localStorage key:', key, e);
      return false;
    }
  }

  // --- CONFIG METHODS ---
  getConfig() {
    return this.get(STORAGE_KEYS.CONFIG, DEFAULT_CONFIG);
  }

  updateConfig(updates) {
    const current = this.getConfig();
    const merged = { ...current, ...updates, lastUpdated: new Date().toISOString() };
    this.save(STORAGE_KEYS.CONFIG, merged);
    return merged;
  }

  // --- SALES / INVOICING METHODS ---
  getSales() {
    return this.get(STORAGE_KEYS.SALES, []);
  }

  getInvoiceById(id) {
    const sales = this.getSales();
    return sales.find(s => s.id === id) || null;
  }

  getNextInvoiceId() {
    const sales = this.getSales();
    const currentYear = new Date().getFullYear();
    const prefix = `CJS-${currentYear}-`;
    
    const matchingNumbers = sales
      .map(s => {
        if (s.id && s.id.startsWith(prefix)) {
          const num = parseInt(s.id.replace(prefix, ''), 10);
          return isNaN(num) ? 0 : num;
        }
        return 0;
      })
      .filter(n => n > 0);

    const nextNum = matchingNumbers.length > 0 ? Math.max(...matchingNumbers) + 1 : 1;
    return `${prefix}${String(nextNum).padStart(4, '0')}`;
  }

  addSale(saleData) {
    const sales = this.getSales();
    const newSale = {
      ...saleData,
      id: saleData.id || this.getNextInvoiceId(),
      createdAt: new Date().toISOString()
    };
    sales.unshift(newSale);
    this.save(STORAGE_KEYS.SALES, sales);
    return newSale;
  }

  updateSale(id, updates) {
    const sales = this.getSales();
    const index = sales.findIndex(s => s.id === id);
    if (index !== -1) {
      sales[index] = { ...sales[index], ...updates };
      this.save(STORAGE_KEYS.SALES, sales);
      return sales[index];
    }
    return null;
  }

  deleteSale(id) {
    const sales = this.getSales().filter(s => s.id !== id);
    this.save(STORAGE_KEYS.SALES, sales);
    return true;
  }

  // --- EXPENSE METHODS ---
  getExpenses() {
    return this.get(STORAGE_KEYS.EXPENSES, []);
  }

  addExpense(expenseData) {
    const expenses = this.getExpenses();
    const newExpense = {
      ...expenseData,
      id: `EXP-${Date.now().toString().slice(-6)}`,
      createdAt: new Date().toISOString()
    };
    expenses.unshift(newExpense);
    this.save(STORAGE_KEYS.EXPENSES, expenses);
    return newExpense;
  }

  deleteExpense(id) {
    const expenses = this.getExpenses().filter(e => e.id !== id);
    this.save(STORAGE_KEYS.EXPENSES, expenses);
    return true;
  }

  // --- AI AGENT ORDERS METHODS ---
  getOrders() {
    return this.get(STORAGE_KEYS.ORDERS, []);
  }

  getOrderById(id) {
    if (!id) return null;
    const clean = String(id).trim().toUpperCase();
    const orders = this.getOrders();
    return orders.find(o => String(o.id || o['Order ID'] || '').trim().toUpperCase() === clean) || null;
  }

  updateOrderStatus(orderId, newStatus) {
    const orders = this.getOrders();
    const index = orders.findIndex(o => o.id === orderId);
    if (index !== -1) {
      orders[index] = { ...orders[index], status: newStatus };
      this.save(STORAGE_KEYS.ORDERS, orders);
      return orders[index];
    }
    return null;
  }

  getEstimatedOrdersCount() {
    const orders = this.getOrders();
    return orders.filter(o => (o.status || '').toLowerCase() === 'estimated').length;
  }

  // --- ASSET & DEPRECIATION METHODS ---
  getAssets() {
    return this.get(STORAGE_KEYS.ASSETS, []);
  }

  addAsset(assetData) {
    const assets = this.getAssets();
    const purchasePrice = parseCurrency(assetData.purchasePrice);
    const usefulLifeMonths = parseInteger(assetData.usefulLifeMonths) || 1;
    const monthlyDepreciation = Number((purchasePrice / usefulLifeMonths).toFixed(2));

    const newAsset = {
      ...assetData,
      purchasePrice,
      usefulLifeMonths,
      monthlyDepreciation,
      id: `AST-${Date.now().toString().slice(-4)}`,
      active: true,
      createdAt: new Date().toISOString()
    };
    assets.unshift(newAsset);
    this.save(STORAGE_KEYS.ASSETS, assets);
    return newAsset;
  }

  deleteAsset(id) {
    const assets = this.getAssets().filter(a => a.id !== id);
    this.save(STORAGE_KEYS.ASSETS, assets);
    return true;
  }

  getTotalMonthlyDepreciation() {
    const assets = this.getAssets();
    return assets
      .filter(a => a.active !== false)
      .reduce((sum, a) => sum + (parseCurrency(a.monthlyDepreciation) || 0), 0);
  }

  // --- CAPITAL METHODS ---
  getCapital() {
    return this.get(STORAGE_KEYS.CAPITAL, []);
  }

  addCapital(capitalData) {
    const capital = this.getCapital();
    const newEntry = {
      ...capitalData,
      amount: parseCurrency(capitalData.amount),
      id: `CAP-${Date.now().toString().slice(-4)}`,
      createdAt: new Date().toISOString()
    };
    capital.unshift(newEntry);
    this.save(STORAGE_KEYS.CAPITAL, capital);
    return newEntry;
  }

  deleteCapital(id) {
    const capital = this.getCapital().filter(c => c.id !== id);
    this.save(STORAGE_KEYS.CAPITAL, capital);
    return true;
  }

  // --- SETTINGS & PIN METHODS ---
  getSettings() {
    return this.get(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
  }

  updateSettings(updates) {
    const current = this.getSettings();
    const merged = { ...current, ...updates };
    this.save(STORAGE_KEYS.SETTINGS, merged);
    return merged;
  }

  verifyPin(pin) {
    const storage = getStorage();
    const stored = storage.getItem(STORAGE_KEYS.PIN) || '8911';
    return stored === pin;
  }

  setPin(newPin) {
    if (newPin && newPin.length === 4) {
      const storage = getStorage();
      storage.setItem(STORAGE_KEYS.PIN, newPin);
      return true;
    }
    return false;
  }

  // --- FINANCIAL CALCULATIONS & KPIS ---
  getMetricsForMonth(year, month) { // month is 0-indexed (0 = Jan, 8 = Sep)
    const sales = this.getSales();
    const expenses = this.getExpenses();
    const monthlyDepreciation = this.getTotalMonthlyDepreciation();

    // Filter sales for the target month
    const monthSales = sales.filter(s => {
      const d = parseSheetDate(s.date);
      if (!d) return false;
      return d.getFullYear() === year && d.getMonth() === month;
    });

    // Filter operational expenses for the target month
    const monthExpenses = expenses.filter(e => {
      const d = parseSheetDate(e.date);
      if (!d) return false;
      return d.getFullYear() === year && d.getMonth() === month;
    });

    const totalRevenue = monthSales.reduce((acc, s) => acc + (parseCurrency(s.grossTotal) || 0), 0);
    const netBilledPreTax = monthSales.reduce((acc, s) => acc + (parseCurrency(s.netPrice) || 0), 0);
    const operationalExpenses = monthExpenses.reduce((acc, e) => acc + (parseCurrency(e.amount) || 0), 0);

    // Total expenses = operational costs + automated monthly equipment depreciation
    const totalExpenses = operationalExpenses + monthlyDepreciation;
    const netProfit = totalRevenue - totalExpenses;
    const netProfitMargin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;

    const totalStitches = monthSales.reduce((acc, s) => acc + (parseInteger(s.totalStitches) || 0), 0);
    const laborHours = monthSales.reduce((acc, s) => acc + (parseCurrency(s.laborHours) || 0), 0);
    const orderCount = monthSales.length;
    const averageOrderValue = orderCount > 0 ? totalRevenue / orderCount : 0;

    return {
      totalRevenue,
      netBilledPreTax,
      operationalExpenses,
      monthlyDepreciation,
      totalExpenses,
      netProfit,
      netProfitMargin,
      totalStitches,
      laborHours,
      orderCount,
      averageOrderValue,
      salesList: monthSales,
      expensesList: monthExpenses
    };
  }

  // All-time / Lifetime Metrics across all records
  getAllTimeMetrics() {
    const sales = this.getSales();
    const expenses = this.getExpenses();
    const monthlyDepreciation = this.getTotalMonthlyDepreciation();

    const totalRevenue = sales.reduce((acc, s) => acc + (parseCurrency(s.grossTotal) || 0), 0);
    const netBilledPreTax = sales.reduce((acc, s) => acc + (parseCurrency(s.netPrice) || 0), 0);
    const operationalExpenses = expenses.reduce((acc, e) => acc + (parseCurrency(e.amount) || 0), 0);
    const totalExpenses = operationalExpenses + monthlyDepreciation;
    const netProfit = totalRevenue - totalExpenses;
    const netProfitMargin = totalRevenue > 0 ? (netProfit / totalRevenue) * 100 : 0;

    const totalStitches = sales.reduce((acc, s) => acc + (parseInteger(s.totalStitches) || 0), 0);
    const laborHours = sales.reduce((acc, s) => acc + (parseCurrency(s.laborHours) || 0), 0);
    const orderCount = sales.length;
    const averageOrderValue = orderCount > 0 ? totalRevenue / orderCount : 0;

    return {
      totalRevenue,
      netBilledPreTax,
      operationalExpenses,
      monthlyDepreciation,
      totalExpenses,
      netProfit,
      netProfitMargin,
      totalStitches,
      laborHours,
      orderCount,
      averageOrderValue,
      salesList: sales,
      expensesList: expenses
    };
  }

  // Available recording periods extracted from data
  getAvailablePeriods() {
    const sales = this.getSales();
    const expenses = this.getExpenses();
    const periods = new Map();

    const addDate = (dateStr) => {
      const d = parseSheetDate(dateStr);
      if (!d) return;
      const key = `${d.getFullYear()}-${d.getMonth()}`;
      if (!periods.has(key)) {
        periods.set(key, {
          year: d.getFullYear(),
          month: d.getMonth(),
          label: d.toLocaleString('default', { month: 'long', year: 'numeric' })
        });
      }
    };

    sales.forEach(s => addDate(s.date));
    expenses.forEach(e => addDate(e.date));

    // Ensure current month is available
    const now = new Date();
    addDate(now.toISOString());

    return Array.from(periods.values()).sort((a, b) => {
      return (b.year * 12 + b.month) - (a.year * 12 + a.month);
    });
  }

  // 6-Month Trend Data for Charts
  getSixMonthTrend() {
    const trend = [];
    const now = new Date();
    
    for (let i = 5; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const metrics = this.getMetricsForMonth(d.getFullYear(), d.getMonth());
      const label = d.toLocaleString('default', { month: 'short', year: '2-digit' });
      trend.push({
        label,
        revenue: Math.round(metrics.totalRevenue),
        expenses: Math.round(metrics.totalExpenses),
        profit: Math.round(metrics.netProfit)
      });
    }

    return trend;
  }

  // Expense Category Breakdown for Current Month or All Time
  getExpenseCategoryBreakdown(year, month) {
    const expenses = this.getExpenses();
    const monthlyDepreciation = this.getTotalMonthlyDepreciation();

    const isAll = year === 'all' || year === null || year === undefined;
    const filtered = isAll
      ? expenses
      : expenses.filter(e => {
          const d = parseSheetDate(e.date);
          if (!d) return false;
          return d.getFullYear() === year && d.getMonth() === month;
        });

    const categoryMap = {
      'Machine Maintenance': 0,
      'Electricity': 0,
      'Cost of Thread': 0,
      'Stabilizer / Backing': 0,
      'Facility / Rent': 0,
      'Miscellaneous / Other': 0,
      'Asset Depreciation': monthlyDepreciation
    };

    for (const exp of filtered) {
      const cat = exp.category || 'Miscellaneous / Other';
      categoryMap[cat] = (categoryMap[cat] || 0) + (parseCurrency(exp.amount) || 0);
    }

    return categoryMap;
  }

  // Export / Import
  exportAllData() {
    return {
      version: '1.0',
      exportedAt: new Date().toISOString(),
      config: this.getConfig(),
      salesLedger: this.getSales(),
      expenseLedger: this.getExpenses(),
      assetLedger: this.getAssets(),
      capitalLedger: this.getCapital(),
      settings: this.getSettings()
    };
  }

  importAllData(jsonObj) {
    if (!jsonObj) return false;
    if (jsonObj.config) this.save(STORAGE_KEYS.CONFIG, jsonObj.config);
    if (jsonObj.salesLedger) this.save(STORAGE_KEYS.SALES, jsonObj.salesLedger);
    if (jsonObj.expenseLedger) this.save(STORAGE_KEYS.EXPENSES, jsonObj.expenseLedger);
    if (jsonObj.assetLedger) this.save(STORAGE_KEYS.ASSETS, jsonObj.assetLedger);
    if (jsonObj.capitalLedger) this.save(STORAGE_KEYS.CAPITAL, jsonObj.capitalLedger);
    if (jsonObj.settings) this.save(STORAGE_KEYS.SETTINGS, jsonObj.settings);
    return true;
  }

  resetToDefault() {
    this.save(STORAGE_KEYS.CONFIG, DEFAULT_CONFIG);
    this.save(STORAGE_KEYS.SALES, []);
    this.save(STORAGE_KEYS.EXPENSES, []);
    this.save(STORAGE_KEYS.ASSETS, []);
    this.save(STORAGE_KEYS.CAPITAL, []);
    this.save(STORAGE_KEYS.CUSTOMERS, []);
    this.save(STORAGE_KEYS.VENDORS, []);
    this.save(STORAGE_KEYS.SETTINGS, DEFAULT_SETTINGS);
    const storage = getStorage();
    storage.setItem(STORAGE_KEYS.PIN, '8911');
    return true;
  }
}

export const storageService = new StorageService();
