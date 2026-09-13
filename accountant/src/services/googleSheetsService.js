// Google Sheets Service for CJS Accountant
// Full synchronization with AI_Agent Google Sheet via Local Express Backend / Cloud Run

import { storageService } from './storageService';

export const APPS_SCRIPT_TEMPLATE = `// Google Apps Script connector fallback (optional if GCP Cloud Run API is used)`;

class GoogleSheetsService {
  constructor() {
    this.status = 'idle';
    this.backendAvailable = false;
    this.isSyncing = false;
    this.lastSyncTime = null;
    this.lastError = null;
    this.subscribers = new Set();
    this.cachedCustomers = [];
    this.cachedVendors = [];
    this.checkBackend();
  }

  subscribe(callback) {
    this.subscribers.add(callback);
    return () => this.subscribers.delete(callback);
  }

  notify(event, data) {
    for (const cb of this.subscribers) {
      try {
        cb(event, data, {
          isSyncing: this.isSyncing,
          backendAvailable: this.backendAvailable,
          lastSyncTime: this.lastSyncTime,
          lastError: this.lastError
        });
      } catch (err) {
        console.error('GoogleSheetsService subscriber error:', err);
      }
    }
  }

  async checkBackend() {
    try {
      const res = await fetch('/api/sheets/status');
      if (res.ok) {
        const data = await res.json();
        this.backendAvailable = Boolean(data.connected);
        this.notify('STATUS_CHECK', data);
        if (data.connected) {
          await this.bootstrapAllData();
        }
        return data;
      }
    } catch (e) {
      this.backendAvailable = false;
      this.notify('STATUS_ERROR', e);
    }
    return null;
  }

  async syncAll(force = false) {
    if (this.isSyncing && !force) return false;
    this.isSyncing = true;
    this.lastError = null;
    this.notify('SYNC_START');

    try {
      // First verify status
      const statusRes = await fetch('/api/sheets/status');
      if (!statusRes.ok) {
        throw new Error(`Server returned HTTP ${statusRes.status}`);
      }
      const statusData = await statusRes.json();
      this.backendAvailable = Boolean(statusData.connected);

      if (!statusData.connected) {
        throw new Error(statusData.error || 'Google Sheet not connected');
      }

      // Then pull all data
      const data = await this.bootstrapAllData();
      this.isSyncing = false;
      this.lastSyncTime = new Date();
      this.notify('SYNC_SUCCESS', data);
      return { success: true, data };
    } catch (err) {
      this.isSyncing = false;
      this.lastError = err.message;
      this.notify('SYNC_ERROR', err);
      throw err;
    }
  }

  async clearCacheAndResync() {
    storageService.resetToDefault();
    return await this.syncAll(true);
  }

  async bootstrapAllData() {
    try {
      const res = await fetch('/api/sheets/bootstrap');
      if (res.ok) {
        const result = await res.json();
        if (result.success && result.data) {
          this.cachedCustomers = result.data.customers || [];
          this.cachedVendors = result.data.vendors || [];
          storageService.hydrateFromSheets(result.data);
          return result.data;
        }
      }
    } catch (e) {
      console.warn('Failed to bootstrap data from Google Sheets:', e);
    }
    return null;
  }

  async testConnection(scriptUrl) {
    try {
      const res = await fetch('/api/sheets/status');
      if (res.ok) {
        const data = await res.json();
        if (data.connected) {
          await this.bootstrapAllData();
          return {
            success: true,
            message: `Connected to Google Sheet: "${data.spreadsheetTitle}" (${data.tabs?.length || 0} tabs synced)`
          };
        } else if (data.serviceAccountEmail) {
          throw new Error(`Please share your Google Sheet with: ${data.serviceAccountEmail} as Editor`);
        }
      }
    } catch (e) {
      if (e.message && e.message.includes('share your Google Sheet')) throw e;
    }

    if (!scriptUrl) throw new Error('Could not connect to Google Sheets backend.');
    return { success: false, message: 'Google Apps Script fallback not active.' };
  }

  async fetchCustomers() {
    try {
      const res = await fetch('/api/sheets/read/Customers');
      if (res.ok) {
        const result = await res.json();
        this.cachedCustomers = result.data || [];
        return this.cachedCustomers;
      }
    } catch (e) {
      console.warn('Failed to fetch customers:', e);
    }
    return [];
  }

  getCustomers() {
    const fromStorage = storageService.getCustomers();
    if (fromStorage && fromStorage.length > 0) return fromStorage;
    return this.cachedCustomers;
  }

  async appendCustomerToSheet(customer) {
    const nextId = `CUST-${Date.now().toString().slice(-4)}`;
    const row = [
      customer.id || nextId,
      customer.name,
      customer.phone || '',
      customer.address || ''
    ];

    storageService.addCustomer({
      id: customer.id || nextId,
      name: customer.name,
      phone: customer.phone || '',
      address: customer.address || ''
    });

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Customers', rowData: row })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing customer to Google Sheet:', e);
    }
    return false;
  }

  async fetchVendors() {
    try {
      const res = await fetch('/api/sheets/read/Vendors');
      if (res.ok) {
        const result = await res.json();
        this.cachedVendors = result.data || [];
        return this.cachedVendors;
      }
    } catch (e) {
      console.warn('Failed to fetch vendors:', e);
    }
    return [];
  }

  getVendors() {
    const fromStorage = storageService.getVendors();
    if (fromStorage && fromStorage.length > 0) return fromStorage;
    return this.cachedVendors;
  }

  async appendVendorToSheet(vendor) {
    const nextId = `VND-${Date.now().toString().slice(-4)}`;
    const row = [
      vendor.id || nextId,
      vendor.name,
      vendor.category || 'General',
      vendor.contactPerson || '',
      vendor.phone || '',
      vendor.address || ''
    ];

    storageService.addVendor({
      id: vendor.id || nextId,
      name: vendor.name,
      category: vendor.category || 'General',
      contactPerson: vendor.contactPerson || '',
      phone: vendor.phone || '',
      address: vendor.address || ''
    });

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Vendors', rowData: row })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing vendor to Google Sheet:', e);
    }
    return false;
  }

  async appendSaleToSheet(sale) {
    const row = [
      sale.date,
      sale.id,
      sale.customer,
      sale.serviceType,
      sale.totalStitches || 0,
      sale.laborHours || 0,
      sale.marginPercent || 0,
      sale.netPrice || 0,
      sale.gst || 0,
      sale.courier || 0,
      sale.grossTotal || 0
    ];

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Sales_Ledger', rowData: row })
      });
      if (res.ok) return true;
    } catch (e) {
      console.warn('Error syncing sale to Google Sheet:', e);
    }
    return false;
  }

  async appendExpenseToSheet(expense) {
    const row = [
      expense.date,
      expense.category,
      expense.description,
      expense.amount,
      expense.paymentMethod
    ];

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Expense_Ledger', rowData: row })
      });
      if (res.ok) return true;
    } catch (e) {
      console.warn('Error syncing expense to Google Sheet:', e);
    }
    return false;
  }

  async appendAssetToSheet(asset) {
    const row = [
      asset.name,
      asset.purchaseDate,
      asset.purchasePrice,
      asset.usefulLifeMonths,
      asset.monthlyDepreciation
    ];

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Asset_Ledger', rowData: row })
      });
      if (res.ok) return true;
    } catch (e) {
      console.warn('Error syncing asset to Google Sheet:', e);
    }
    return false;
  }

  async appendCapitalToSheet(capital) {
    const row = [
      capital.date,
      capital.transactionType,
      capital.description,
      capital.amount
    ];

    try {
      const res = await fetch('/api/sheets/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sheetName: 'Capital_Ledger', rowData: row })
      });
      if (res.ok) return true;
    } catch (e) {
      console.warn('Error syncing capital to Google Sheet:', e);
    }
    return false;
  }

  async fetchOrders() {
    try {
      const res = await fetch('/api/sheets/orders');
      if (res.ok) {
        const result = await res.json();
        if (result.success && result.orders) {
          const mappedOrders = result.orders.map((o, idx) => {
            let stitchCount = 0;
            const rawStitch = o['Stitch Count'] || o.stitchCount || '';
            const reasoningText = o['Reasoning '] || o['Reasoning'] || o.reasoning || '';
            if (typeof rawStitch === 'string' && rawStitch.includes('-')) {
              // Date formatting anomaly in Google Sheets (e.g. 1918-02-03)
              const match = reasoningText.match(/(\d+)\s+total stitches/i) || reasoningText.match(/(\d+)\s*st\b/i);
              stitchCount = match ? parseInt(match[1], 10) : parseInt(rawStitch, 10) || 0;
            } else {
              stitchCount = parseInt(rawStitch || 0, 10) || 0;
              if (stitchCount === 0 && reasoningText) {
                const match = reasoningText.match(/(\d+)\s+total stitches/i) || reasoningText.match(/(\d+)\s*st\b/i);
                if (match) stitchCount = parseInt(match[1], 10);
              }
            }

            const orderType = o['Order Type'] || o['Embroidery Type'] || o.orderType || o.embroideryType || '';

            return {
              id: o['Order ID'] || o.id || `ORD-${idx + 1}`,
              orderDate: o['Order Date'] || o.orderDate || '',
              customerId: o['Customer ID'] || o.customerId || '',
              customerName: o['Customer Name'] || o.customerName || '',
              phone: o['Phone'] || o.phone || '',
              orderType: orderType,
              templateName: o['Template Name'] || o.templateName || '',
              quantity: parseInt(o['Quantity'] || o.quantity || 1, 10) || 1,
              laborHours: parseFloat(o['Labor Hours'] || o.laborHours || 0) || 0,
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
              overrideMachine: o['Override Machine'] || o.overrideMachine || ''
            };
          });
          storageService.save('cjs_ai_orders', mappedOrders);
          return mappedOrders;
        }
      }
    } catch (e) {
      console.warn('Failed to fetch orders:', e);
    }
    return storageService.getOrders();
  }

  async updateOrderStatus(orderId, status) {
    // 1. Immediately update locally for instantaneous UI response
    storageService.updateOrderStatus(orderId, status);

    // 2. Sync to Google Sheets
    try {
      const res = await fetch('/api/sheets/orders/status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ orderId, status })
      });
      if (res.ok) {
        const data = await res.json();
        return { success: true, data };
      } else {
        const errData = await res.json().catch(() => ({}));
        return { success: false, error: errData.error || 'Server error updating status' };
      }
    } catch (e) {
      console.warn('Error updating order status in Google Sheets:', e);
      return { success: false, error: e.message };
    }
  }
}

export const googleSheetsService = new GoogleSheetsService();
