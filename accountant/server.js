import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { Firestore } from '@google-cloud/firestore';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8080;
const PROJECT_ID = process.env.GCP_PROJECT_ID || 'cjs-designs-501004';

app.use(cors());
app.use(express.json());

// Initialize Firestore Native Database Client
let db;
const keyPath = path.join(__dirname, 'service-account-key.json');
const rootKeyPath = path.join(__dirname, '..', 'service-account-key.json');

try {
  if (fs.existsSync(keyPath)) {
    db = new Firestore({ projectId: PROJECT_ID, keyFilename: keyPath });
  } else if (fs.existsSync(rootKeyPath)) {
    db = new Firestore({ projectId: PROJECT_ID, keyFilename: rootKeyPath });
  } else if (process.env.GOOGLE_CREDENTIALS_JSON) {
    const credentials = JSON.parse(process.env.GOOGLE_CREDENTIALS_JSON);
    db = new Firestore({ projectId: PROJECT_ID, credentials });
  } else {
    // Cloud Run Application Default Credentials
    db = new Firestore({ projectId: PROJECT_ID });
  }
  console.log(`[Firestore Database] Connected to GCP project: ${PROJECT_ID}`);
} catch (err) {
  console.error('[Firestore Database] Initialization error:', err);
}

// -----------------------------------------------------------------
// Helper to normalize collection names from Google Sheet tab names
// -----------------------------------------------------------------
function getCollectionName(sheetName) {
  const map = {
    'Orders': 'orders',
    'Customers': 'customers',
    'Vendors': 'vendors',
    'Description_Templates': 'description_templates',
    'Config': 'config',
    'Holidays': 'holidays',
    'Reminders': 'reminders',
    'Sales_Ledger': 'sales_ledger',
    'Expense_Ledger': 'expense_ledger',
    'Asset_Ledger': 'asset_ledger',
    'Capital_Ledger': 'capital_ledger'
  };
  return map[sheetName] || sheetName.toLowerCase().replace(/[\s-]+/g, '_');
}

// API: Media Image Proxy (Bypasses CORS for html2canvas, prevents canvas tainting)
app.get('/api/media/proxy', async (req, res) => {
  const imageUrl = req.query.url;
  if (!imageUrl) return res.status(400).send('Missing url parameter');
  try {
    const upstream = await fetch(imageUrl);
    if (!upstream.ok) {
      return res.status(upstream.status).send('Failed to fetch image');
    }
    const contentType = upstream.headers.get('content-type') || 'image/jpeg';
    res.setHeader('Content-Type', contentType);
    res.setHeader('Cache-Control', 'public, max-age=86400');
    res.setHeader('Access-Control-Allow-Origin', '*');
    const arrayBuffer = await upstream.arrayBuffer();
    return res.send(Buffer.from(arrayBuffer));
  } catch (err) {
    console.error('[ImageProxy] Error fetching upstream image:', err.message);
    return res.status(500).send('Image proxy error');
  }
});

// API: Test Connection & Get Database Metadata
const handleStatus = async (req, res) => {
  try {
    if (!db) throw new Error('Firestore database client not initialized');
    const collections = await db.listCollections();
    const tabs = collections.map(c => c.id);

    return res.json({
      connected: true,
      database: 'Firestore (Native Google Cloud)',
      projectId: PROJECT_ID,
      collections: [
        'config', 'sales_ledger', 'expense_ledger', 'asset_ledger',
        'capital_ledger', 'customers', 'vendors', 'description_templates',
        'orders', 'reminders', 'holidays'
      ],
      tabs: [
        'Config', 'Sales_Ledger', 'Expense_Ledger', 'Asset_Ledger',
        'Capital_Ledger', 'Customers', 'Vendors', 'Description_Templates',
        'Orders', 'Reminders', 'Holidays'
      ]
    });
  } catch (err) {
    return res.status(500).json({ connected: false, error: err.message });
  }
};

app.get('/api/status', handleStatus);
app.get('/api/db/status', handleStatus);
app.get('/api/sheets/status', handleStatus); // Backwards-compatibility alias

// API: Initialize Database (No-op since collections are self-provisioning in Firestore)
const handleInit = async (req, res) => {
  return res.json({
    success: true,
    message: 'Google Cloud Firestore database active and self-provisioning'
  });
};

app.post('/api/init', handleInit);
app.post('/api/db/init', handleInit);
app.post('/api/sheets/init', handleInit); // Backwards-compatibility alias

// API: Bootstrap all application data from Firestore in one high-speed call
const handleBootstrap = async (req, res) => {
  try {
    if (!db) throw new Error('Database not connected');

    const [
      custSnap,
      vendSnap,
      salesSnap,
      expSnap,
      assetSnap,
      capSnap,
      ordersSnap,
      tmplSnap,
      configSnap,
      holidaysSnap
    ] = await Promise.all([
      db.collection('customers').get(),
      db.collection('vendors').get(),
      db.collection('sales_ledger').get(),
      db.collection('expense_ledger').get(),
      db.collection('asset_ledger').get(),
      db.collection('capital_ledger').get(),
      db.collection('orders').get(),
      db.collection('description_templates').get(),
      db.collection('config').get(),
      db.collection('holidays').get()
    ]);

    // Format customers with Sheet header aliases for frontend compatibility
    const customers = custSnap.docs.map(d => {
      const data = d.data();
      return {
        id: data.customer_id || d.id,
        'Customer ID': data.customer_id || d.id,
        name: data.name || '',
        'Name': data.name || '',
        phone: data.phone || '',
        'Phone': data.phone || '',
        address: data.address || '',
        'Address': data.address || ''
      };
    });

    // Format vendors
    const vendors = vendSnap.docs.map(d => {
      const data = d.data();
      return {
        id: data.vendor_id || d.id,
        'Vendor ID': data.vendor_id || d.id,
        name: data.name || '',
        'Name': data.name || '',
        category: data.category || '',
        'Category': data.category || '',
        contactPerson: data.contact_person || '',
        'Contact Person': data.contact_person || '',
        phone: data.phone || '',
        'Phone': data.phone || '',
        address: data.address || '',
        'Address': data.address || ''
      };
    });

    // Format sales
    const sales = salesSnap.docs.map(d => {
      const data = d.data();
      const lHrs = Number(data.labor_hrs || data.labor_hours || 0);
      const lMins = data.labor_minutes !== undefined ? Number(data.labor_minutes) : Math.round(lHrs * 60);
      return {
        id: data.invoice_id || d.id,
        'Invoice ID': data.invoice_id || d.id,
        date: data.date || '',
        'Date': data.date || '',
        customer: data.customer || '',
        'Customer': data.customer || '',
        serviceType: data.service_type || '',
        'Service Type': data.service_type || '',
        totalStitches: data.total_stitches || 0,
        'Total Stitches': data.total_stitches || 0,
        laborHours: lHrs,
        'Labor Hrs': lHrs,
        laborMinutes: lMins,
        'Labor Minutes': lMins,
        marginPercent: data.margin_pct || 0,
        'Margin %': data.margin_pct || 0,
        netPrice: data.net_price || 0,
        'Net Price': data.net_price || 0,
        gst: data.gst || 0,
        'GST': data.gst || 0,
        courier: data.courier || 0,
        'Courier': data.courier || 0,
        grossTotal: data.gross_total || 0,
        'Gross Total': data.gross_total || 0,
        status: data.status || 'Paid',
        imageUrl: data.image_url || data.imageUrl || '',
        'Image URL': data.image_url || data.imageUrl || ''
      };
    });

    // Format expenses
    const expenses = expSnap.docs.map(d => {
      const data = d.data();
      return {
        id: data.id || d.id,
        date: data.date || '',
        'Date': data.date || '',
        category: data.category || '',
        'Expense Category': data.category || '',
        description: data.description || '',
        'Description': data.description || '',
        amount: data.amount || 0,
        'Amount': data.amount || 0,
        paymentMethod: data.payment_method || 'UPI',
        'Payment Method': data.payment_method || 'UPI'
      };
    });

    // Format assets
    const assets = assetSnap.docs.map(d => {
      const data = d.data();
      return {
        id: data.id || d.id,
        name: data.name || '',
        'Asset Name': data.name || '',
        purchaseDate: data.purchase_date || '',
        'Purchase Date': data.purchase_date || '',
        purchasePrice: data.purchase_price || 0,
        'Purchase Price': data.purchase_price || 0,
        usefulLifeMonths: data.useful_life_months || 36,
        'Useful Life (Months)': data.useful_life_months || 36,
        monthlyDepreciation: data.monthly_depreciation || 0,
        'Monthly Depreciation': data.monthly_depreciation || 0
      };
    });

    // Format capital
    const capital = capSnap.docs.map(d => {
      const data = d.data();
      return {
        id: data.id || d.id,
        date: data.date || '',
        'Date': data.date || '',
        transactionType: data.transaction_type || 'Investment',
        'Transaction Type': data.transaction_type || 'Investment',
        description: data.description || '',
        'Description': data.description || '',
        amount: data.amount || 0,
        'Amount': data.amount || 0
      };
    });

    // Format orders
    const orders = ordersSnap.docs.map(d => {
      const data = d.data();
      const lHrs = Number(data.labor_hours || 0);
      const lMins = data.labor_minutes !== undefined ? Number(data.labor_minutes) : Math.round(lHrs * 60);
      return {
        id: data.order_id || d.id,
        'Order ID': data.order_id || d.id,
        orderDate: data.order_date || '',
        'Order Date': data.order_date || '',
        customerId: data.customer_id || '',
        'Customer ID': data.customer_id || '',
        customerName: data.customer_name || '',
        'Customer Name': data.customer_name || '',
        phone: data.phone || '',
        'Phone': data.phone || '',
        orderType: data.order_type || 'Machine Embroidery',
        'Order Type': data.order_type || 'Machine Embroidery',
        templateName: data.template_name || '',
        'Template Name': data.template_name || '',
        quantity: data.quantity || 1,
        'Quantity': data.quantity || 1,
        stitchCount: data.stitch_count || 0,
        'Stitch Count': data.stitch_count || 0,
        laborHours: lHrs,
        'Labor Hours': lHrs,
        laborMinutes: lMins,
        'Labor Minutes': lMins,
        machine: data.machine || 'None',
        'Machine': data.machine || 'None',
        estimatedDeliveryDate: data.estimated_delivery_date || '',
        'Estimated Delivery Date': data.estimated_delivery_date || '',
        estimatedCost: data.estimated_cost || '',
        'Estimated Cost': data.estimated_cost || '',
        status: data.payment_status || 'Estimated',
        'Payment Status': data.payment_status || 'Estimated',
        reasoning: data.reasoning || '',
        'Reasoning': data.reasoning || '',
        overrides: data.overrides || '',
        'Overrides': data.overrides || '',
        imageUrl: data.image_url || data.imageUrl || data['Image URL'] || '',
        'Image URL': data.image_url || data.imageUrl || data['Image URL'] || '',
        image_url: data.image_url || data.imageUrl || data['Image URL'] || ''
      };
    });

    // Format templates
    const descriptionTemplates = tmplSnap.docs.map(d => {
      const data = d.data();
      return {
        id: d.id,
        templateName: data.template_name || '',
        'Template Name': data.template_name || '',
        serviceCategory: data.service_category || 'Machine Embroidery',
        'Service Category': data.service_category || 'Machine Embroidery',
        description: data.description || '',
        'Description': data.description || '',
        machine: data.machine || 'None',
        'Machine': data.machine || 'None',
        laborMinutes: data.labor_minutes || 60,
        'Labor Minutes': data.labor_minutes || 60,
        stitchCount: data.stitch_count || 0,
        'Stitch Count': data.stitch_count || 0
      };
    });

    // Format config
    const config = {};
    configSnap.docs.forEach(d => {
      const data = d.data();
      config[data.key || d.id] = data.value;
    });

    // Format holidays
    const holidays = holidaysSnap.docs.map(d => d.data());

    return res.json({
      success: true,
      data: {
        customers,
        vendors,
        sales,
        expenses,
        assets,
        capital,
        orders,
        descriptionTemplates,
        config,
        holidays
      }
    });
  } catch (err) {
    console.error('[Firestore] Bootstrap error:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
};

app.get('/api/bootstrap', handleBootstrap);
app.get('/api/db/bootstrap', handleBootstrap);
app.get('/api/sheets/bootstrap', handleBootstrap); // Backwards-compatibility alias

// =================================================================
// ORDERS & DATABASE REST ENDPOINTS
// =================================================================

// Handler: Read all orders from Firestore orders collection
const handleGetOrders = async (req, res) => {
  try {
    const snap = await db.collection('orders').get();
    const orders = snap.docs.map((d, idx) => {
      const data = d.data();
      const currentStatus = data.payment_status || data.status || 'Estimated';
      return {
        rowIndex: idx + 2,
        id: data.order_id || d.id,
        'Order ID': data.order_id || d.id,
        orderDate: data.order_date || '',
        'Order Date': data.order_date || '',
        customerId: data.customer_id || '',
        'Customer ID': data.customer_id || '',
        customerName: data.customer_name || '',
        'Customer Name': data.customer_name || '',
        phone: data.phone || '',
        'Phone': data.phone || '',
        orderType: data.order_type || '',
        'Order Type': data.order_type || '',
        templateName: data.template_name || '',
        'Template Name': data.template_name || '',
        quantity: data.quantity || 1,
        'Quantity': data.quantity || 1,
        stitchCount: data.stitch_count || 0,
        'Stitch Count': data.stitch_count || 0,
        laborHours: data.labor_hours || 0,
        'Labor Hours': data.labor_hours || 0,
        laborMinutes: data.labor_minutes !== undefined ? Number(data.labor_minutes) : Math.round(Number(data.labor_hours || 0) * 60),
        'Machine': data.machine || '',
        estimatedDeliveryDate: data.estimated_delivery_date || '',
        'Estimated Delivery Date': data.estimated_delivery_date || '',
        estimatedCost: data.estimated_cost || '',
        'Estimated Cost': data.estimated_cost || '',
        paymentStatus: currentStatus,
        'Payment Status': currentStatus,
        status: currentStatus,
        reasoning: data.reasoning || '',
        'Reasoning': data.reasoning || '',
        imageUrl: data.image_url || data.imageUrl || data['Image URL'] || '',
        'Image URL': data.image_url || data.imageUrl || data['Image URL'] || '',
        image_url: data.image_url || data.imageUrl || data['Image URL'] || ''
      };
    });
    return res.json({ success: true, orders });
  } catch (err) {
    return res.status(500).json({ success: false, error: err.message });
  }
};

app.get('/api/orders', handleGetOrders);
app.get('/api/sheets/orders', handleGetOrders); // Backwards-compatibility alias

// Handler: Update order status (instant 10ms execution in Firestore)
const handleUpdateOrderStatus = async (req, res) => {
  try {
    const { orderId, status } = req.body;
    if (!orderId || !status) {
      return res.status(400).json({ error: 'Missing orderId or status' });
    }

    const cleanId = String(orderId).trim();
    let docRef = db.collection('orders').doc(cleanId);
    let docSnap = await docRef.get();
    if (!docSnap.exists) {
      const upperRef = db.collection('orders').doc(cleanId.toUpperCase());
      const upperSnap = await upperRef.get();
      if (upperSnap.exists) {
        docRef = upperRef;
      } else {
        // Query by order_id field
        const qSnap = await db.collection('orders').where('order_id', '==', cleanId).get();
        if (!qSnap.empty) {
          docRef = qSnap.docs[0].ref;
        } else {
          const qUpperSnap = await db.collection('orders').where('order_id', '==', cleanId.toUpperCase()).get();
          if (!qUpperSnap.empty) {
            docRef = qUpperSnap.docs[0].ref;
          }
        }
      }
    }

    await docRef.set({
      payment_status: status,
      status: status,
      updated_at: new Date().toISOString()
    }, { merge: true });

    return res.json({
      success: true,
      orderId: docRef.id,
      status
    });
  } catch (err) {
    console.error('[OrdersStatus] Error:', err);
    return res.status(500).json({ success: false, error: err.message });
  }
};

app.post('/api/orders/status', handleUpdateOrderStatus);
app.post('/api/sheets/orders/status', handleUpdateOrderStatus); // Backwards-compatibility alias

// Handler: Append single document to a collection
const handleAppendRow = async (req, res) => {
  try {
    const { sheetName, collection, rowData, data } = req.body;
    const targetName = collection || sheetName;
    const payload = data || rowData;
    if (!targetName || !payload) {
      return res.status(400).json({ error: 'Missing collection name or payload' });
    }
    const collectionName = getCollectionName(targetName);
    const docId = payload.id || payload['Invoice ID'] || payload['Order ID'] || payload['Customer ID'] || `doc_${Date.now()}`;
    await db.collection(collectionName).doc(String(docId)).set(payload, { merge: true });

    return res.json({ success: true, id: docId });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
};

app.post('/api/db/append', handleAppendRow);
app.post('/api/sheets/append', handleAppendRow); // Backwards-compatibility alias

// Handler: Batch append documents
const handleBatchAppend = async (req, res) => {
  try {
    const { sheetName, collection, rows, data } = req.body;
    const targetName = collection || sheetName;
    const records = data || rows;
    if (!targetName || !Array.isArray(records)) {
      return res.status(400).json({ error: 'Missing collection name or records array' });
    }
    const collectionName = getCollectionName(targetName);
    const batch = db.batch();
    records.forEach(r => {
      const docId = r.id || r['Invoice ID'] || r['Order ID'] || r['Customer ID'] || null;
      const docRef = docId ? db.collection(collectionName).doc(String(docId)) : db.collection(collectionName).doc();
      batch.set(docRef, r, { merge: true });
    });
    await batch.commit();
    return res.json({ success: true, count: records.length });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
};

app.post('/api/db/batch-append', handleBatchAppend);
app.post('/api/sheets/batch-append', handleBatchAppend); // Backwards-compatibility alias

// API: Read collection
const handleReadCollection = async (req, res) => {
  try {
    const targetName = req.params.collectionName || req.params.sheetName;
    const collectionName = getCollectionName(targetName);
    const snap = await db.collection(collectionName).get();
    const data = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    return res.json({ headers: [], data });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
};

app.get('/api/db/read/:collectionName', handleReadCollection);
app.get('/api/sheets/read/:sheetName', handleReadCollection); // Backwards-compatibility alias

// -----------------------------------------------------------------
// MASTER DATA MANAGEMENT REST ENDPOINTS (Config, Holidays, Customers, Vendors, Templates)
// -----------------------------------------------------------------

// Config
app.get('/api/config', async (req, res) => {
  try {
    const snap = await db.collection('config').get();
    const config = {};
    snap.docs.forEach(d => { config[d.id] = d.data().value; });
    return res.json({ success: true, config });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/config', async (req, res) => {
  try {
    const { key, value } = req.body;
    if (!key) return res.status(400).json({ error: 'Missing key' });
    await db.collection('config').doc(key).set({
      key,
      value,
      last_updated: new Date().toISOString()
    });
    return res.json({ success: true, key, value });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Holidays
app.get('/api/holidays', async (req, res) => {
  try {
    const snap = await db.collection('holidays').get();
    const holidays = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    return res.json({ success: true, holidays });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/holidays', async (req, res) => {
  try {
    const { date, event } = req.body;
    if (!date || !event) return res.status(400).json({ error: 'Missing date or event' });
    const docId = date.replace(/[^a-zA-Z0-9_-]/g, '_');
    await db.collection('holidays').doc(docId).set({ date, event });
    return res.json({ success: true, id: docId });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.delete('/api/holidays/:id', async (req, res) => {
  try {
    await db.collection('holidays').doc(req.params.id).delete();
    return res.json({ success: true });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Customers
app.get('/api/customers', async (req, res) => {
  try {
    const snap = await db.collection('customers').get();
    const customers = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    return res.json({ success: true, customers });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/customers', async (req, res) => {
  try {
    const { customer_id, name, phone, address } = req.body;
    if (!name) return res.status(400).json({ error: 'Missing name' });
    const cid = customer_id || `CUST-${Date.now()}`;
    await db.collection('customers').doc(cid).set({
      customer_id: cid,
      name,
      phone: phone || '',
      address: address || '',
      updated_at: new Date().toISOString()
    }, { merge: true });
    return res.json({ success: true, customer_id: cid });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Vendors
app.get('/api/vendors', async (req, res) => {
  try {
    const snap = await db.collection('vendors').get();
    const vendors = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    return res.json({ success: true, vendors });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/vendors', async (req, res) => {
  try {
    const { vendor_id, name, category, contact_person, phone, address } = req.body;
    if (!name) return res.status(400).json({ error: 'Missing name' });
    const vid = vendor_id || `VND-${Date.now()}`;
    await db.collection('vendors').doc(vid).set({
      vendor_id: vid,
      name,
      category: category || '',
      contact_person: contact_person || '',
      phone: phone || '',
      address: address || ''
    }, { merge: true });
    return res.json({ success: true, vendor_id: vid });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Templates
app.get('/api/templates', async (req, res) => {
  try {
    const snap = await db.collection('description_templates').get();
    const templates = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    return res.json({ success: true, templates });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

app.post('/api/templates', async (req, res) => {
  try {
    const { template_name, service_category, description, machine, labor_minutes, stitch_count } = req.body;
    if (!template_name) return res.status(400).json({ error: 'Missing template_name' });
    const docId = template_name.replace(/[^a-zA-Z0-9_-]/g, '_');
    await db.collection('description_templates').doc(docId).set({
      template_name,
      service_category: service_category || 'Machine Embroidery',
      description: description || '',
      machine: machine || 'None',
      labor_minutes: Number(labor_minutes) || 60,
      stitch_count: Number(stitch_count) || 0
    }, { merge: true });
    return res.json({ success: true, id: docId });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Serve built frontend assets
const distPath = path.join(__dirname, 'dist');
if (fs.existsSync(distPath)) {
  app.use((req, res, next) => {
    if (req.path === '/' || req.path.endsWith('.html') || req.path.endsWith('sw.js') || req.path.endsWith('manifest.json')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    }
    next();
  });
  app.use(express.static(distPath));
  app.use((req, res) => {
    res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    res.sendFile(path.join(distPath, 'index.html'));
  });
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`CJS Accountant server running on port ${PORT} backed by Google Cloud Firestore`);
});
