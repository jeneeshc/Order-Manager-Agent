// Cloud Database Service for CJS Accountant
// Full synchronization with Google Cloud Firestore backend via Cloud Run Express API

import { storageService } from './storageService';

export const APPS_SCRIPT_TEMPLATE = '// Cloud Firestore native backend is active';

class DatabaseService {
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
        console.error('DatabaseService subscriber error:', err);
      }
    }
  }

  async checkBackend() {
    try {
      const res = await fetch('/api/status');
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
      const statusRes = await fetch('/api/status');
      if (!statusRes.ok) {
        throw new Error(`Server returned HTTP ${statusRes.status}`);
      }
      const statusData = await statusRes.json();
      this.backendAvailable = Boolean(statusData.connected);

      if (!statusData.connected) {
        throw new Error(statusData.error || 'Cloud Database not connected');
      }

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
      const res = await fetch('/api/bootstrap');
      if (res.ok) {
        const result = await res.json();
        if (result.success && result.data) {
          this.cachedCustomers = result.data.customers || [];
          this.cachedVendors = result.data.vendors || [];
          storageService.hydrateFromDatabase(result.data);
          return result.data;
        }
      }
    } catch (e) {
      console.warn('Failed to bootstrap data from database:', e);
    }
    return null;
  }

  async fetchCustomers() {
    try {
      const res = await fetch('/api/customers');
      if (res.ok) {
        const result = await res.json();
        this.cachedCustomers = result.customers || [];
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

  async saveCustomer(customer) {
    const nextId = customer.id || `CUST-${Date.now().toString().slice(-4)}`;
    const record = {
      id: nextId,
      name: customer.name,
      phone: customer.phone || '',
      address: customer.address || ''
    };

    storageService.addCustomer(record);

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'customers', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing customer to database:', e);
    }
    return false;
  }

  async appendCustomerToSheet(customer) {
    return this.saveCustomer(customer);
  }

  async fetchVendors() {
    try {
      const res = await fetch('/api/vendors');
      if (res.ok) {
        const result = await res.json();
        this.cachedVendors = result.vendors || [];
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

  async saveVendor(vendor) {
    const nextId = vendor.id || `VND-${Date.now().toString().slice(-4)}`;
    const record = {
      id: nextId,
      name: vendor.name,
      category: vendor.category || 'General',
      contactPerson: vendor.contactPerson || '',
      phone: vendor.phone || '',
      address: vendor.address || ''
    };

    storageService.addVendor(record);

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'vendors', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing vendor to database:', e);
    }
    return false;
  }

  async appendVendorToSheet(vendor) {
    return this.saveVendor(vendor);
  }

  async saveSale(sale) {
    const record = {
      id: sale.id,
      invoice_id: sale.id,
      date: sale.date,
      customer: sale.customer,
      customerPhone: sale.customerPhone || '',
      customerAddress: sale.customerAddress || '',
      serviceType: sale.serviceType,
      service_type: sale.serviceType,
      description: sale.description || '',
      totalStitches: sale.totalStitches || 0,
      total_stitches: sale.totalStitches || 0,
      laborMinutes: sale.laborMinutes || 0,
      labor_minutes: sale.laborMinutes || 0,
      laborHours: sale.laborHours || 0,
      labor_hours: sale.laborHours || 0,
      marginPercent: sale.marginPercent || 0,
      margin_pct: sale.marginPercent || 0,
      netPrice: sale.netPrice || 0,
      net_price: sale.netPrice || 0,
      gst: sale.gst || 0,
      courier: sale.courier || 0,
      grossTotal: sale.grossTotal || 0,
      gross_total: sale.grossTotal || 0,
      status: sale.status || 'Paid',
      imageUrl: sale.imageUrl || '',
      image_url: sale.imageUrl || '',
      orderRef: sale.orderRef || null,
      order_id: sale.orderRef || null,
      created_at: new Date().toISOString()
    };

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'sales_ledger', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing sale to Firestore database:', e);
    }
    return false;
  }

  async appendSaleToSheet(sale) {
    return this.saveSale(sale);
  }

  async saveExpense(expense) {
    const record = {
      id: expense.id || `EXP-${Date.now().toString().slice(-6)}`,
      date: expense.date,
      category: expense.category,
      description: expense.description,
      amount: expense.amount,
      paymentMethod: expense.paymentMethod || 'UPI',
      created_at: new Date().toISOString()
    };

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'expense_ledger', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing expense to database:', e);
    }
    return false;
  }

  async appendExpenseToSheet(expense) {
    return this.saveExpense(expense);
  }

  async saveAsset(asset) {
    const record = {
      id: asset.id || `AST-${Date.now().toString().slice(-4)}`,
      name: asset.name,
      purchaseDate: asset.purchaseDate,
      purchasePrice: asset.purchasePrice,
      usefulLifeMonths: asset.usefulLifeMonths,
      monthlyDepreciation: asset.monthlyDepreciation,
      created_at: new Date().toISOString()
    };

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'asset_ledger', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing asset to database:', e);
    }
    return false;
  }

  async appendAssetToSheet(asset) {
    return this.saveAsset(asset);
  }

  async saveCapital(capital) {
    const record = {
      id: capital.id || `CAP-${Date.now().toString().slice(-4)}`,
      date: capital.date,
      transactionType: capital.transactionType,
      description: capital.description,
      amount: capital.amount,
      created_at: new Date().toISOString()
    };

    try {
      const res = await fetch('/api/db/append', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ collection: 'capital_ledger', data: record })
      });
      return res.ok;
    } catch (e) {
      console.warn('Error syncing capital to database:', e);
    }
    return false;
  }

  async appendCapitalToSheet(capital) {
    return this.saveCapital(capital);
  }

  async fetchOrders() {
    try {
      const res = await fetch('/api/orders');
      if (res.ok) {
        const result = await res.json();
        if (result.success && result.orders) {
          const mappedOrders = result.orders.map((o, idx) => {
            const stitchCount = parseInt(o.stitchCount || o['Stitch Count'] || 0, 10) || 0;
            const orderType = o.orderType || o['Order Type'] || o.embroideryType || 'Machine Embroidery';
            const currentStatus = o.status || o.paymentStatus || o['Payment Status'] || 'Estimated';

            return {
              id: o.id || o['Order ID'] || `ORD-${idx + 1}`,
              orderDate: o.orderDate || o['Order Date'] || '',
              customerId: o.customerId || o['Customer ID'] || '',
              customerName: o.customerName || o['Customer Name'] || '',
              phone: o.phone || o['Phone'] || '',
              orderType,
              templateName: o.templateName || o['Template Name'] || '',
              quantity: parseInt(o.quantity || o['Quantity'] || 1, 10) || 1,
              laborHours: parseFloat(o.laborHours || o['Labor Hours'] || 0) || 0,
              laborMinutes: o.laborMinutes !== undefined ? parseInt(o.laborMinutes, 10) : Math.round(parseFloat(o.laborHours || 0) * 60),
              material: o.material || o['Material'] || '',
              embroideryType: orderType,
              stitchCount,
              machine: o.machine || o['Machine'] || '',
              estimatedDeliveryDate: o.estimatedDeliveryDate || o['Estimated Delivery Date'] || '',
              estimatedCost: o.estimatedCost || o['Estimated Cost'] || '',
              status: currentStatus,
              paymentStatus: currentStatus,
              'Payment Status': currentStatus,
              reasoning: o.reasoning || o['Reasoning'] || '',
              imageUrl: o.imageUrl || o.image_url || o['Image URL'] || ''
            };
          });
          storageService.save('cjs_ai_orders', mappedOrders);
          return mappedOrders;
        }
      }
    } catch (e) {
      console.warn('Failed to fetch orders from database:', e);
    }
    return storageService.getOrders();
  }

  async updateOrderStatus(orderId, status) {
    // 1. Immediately update locally in storageService for instantaneous UI update
    storageService.updateOrderStatus(orderId, status);

    // 2. Sync to Firestore native database
    try {
      const res = await fetch('/api/orders/status', {
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
      console.warn('Error updating order status in database:', e);
      return { success: false, error: e.message };
    }
  }
}

export const databaseService = new DatabaseService();
export const googleSheetsService = databaseService; // Seamless backward-compatibility
