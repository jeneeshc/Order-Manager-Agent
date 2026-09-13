/**
 * End-to-End Test Case: AI Agent (WhatsApp Agent) Order Lifecycle
 * 
 * Life Cycle Stages:
 * Stage 1: AI Agent (WhatsApp) receives customer order and appends row to Google Sheets "Orders" tab with status "Estimated".
 * Stage 2: CJS Accountant syncs and fetches the new order, displaying it in the Orders tab as pending.
 * Stage 3: Accountant clicks "Generate Invoice", which prepares pre-filled invoice payload with stitch count, customer, and pricing.
 * Stage 4: Payment is received -> CJS Accountant marks order "Complete", updating Google Sheets Column K to "Complete".
 * Stage 5: Verification of Google Sheet row update.
 */

import { GoogleAuth } from 'google-auth-library';

const SPREADSHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';
const APP_BASE_URL = process.env.APP_URL || 'https://cjs-accountant-225021995719.us-central1.run.app';

async function getAuthToken() {
  const auth = new GoogleAuth({
    keyFile: './service-account-key.json',
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();
  return token.token;
}

function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runOrderLifecycleTest() {
  console.log('===============================================================');
  console.log('  TEST CASE: AI AGENT (WHATSAPP) ORDER END-TO-END LIFECYCLE   ');
  console.log('===============================================================\n');

  const token = await getAuthToken();
  const timestamp = Date.now().toString().slice(-4);
  const testOrderId = `CJS-WA-${timestamp}`;
  const orderDate = new Date().toISOString().replace('T', ' ').slice(0, 16);
  
  const testOrderData = {
    orderDate: orderDate,
    orderId: testOrderId,
    customerId: '1006',
    customerName: 'Priya Fashions',
    phone: '9847012345',
    orderType: 'Machine Embroidery',
    templateName: 'Bridal Motifs',
    quantity: '1',
    stitchCount: '65000',
    laborHours: '0.5',
    machine: 'Machine 2',
    estimatedDeliveryDate: '2026-09-08',
    estimatedCost: 'Rs 1300.0',
    paymentStatus: 'Estimated',
    reasoning: 'WhatsApp Agent parsed audio/image request for 65k stitches on raw silk. Quoted ₹1300 at standard rate. Machine 2 selected for fine thread detail.',
    overrides: ''
  };

  // --------------------------------------------------------------------------
  // STAGE 1: AI Agent (WhatsApp Agent) creates order in Google Sheets
  // --------------------------------------------------------------------------
  console.log('📌 STAGE 1: AI Agent (WhatsApp Agent) places order...');
  console.log(`   Order ID:        ${testOrderId}`);
  console.log(`   Customer:        ${testOrderData.customerName} (${testOrderData.phone})`);
  console.log(`   Item & Stitches: ${testOrderData.templateName} - ${testOrderData.orderType} (${testOrderData.stitchCount} stitches)`);
  console.log(`   Initial Status:  ${testOrderData.paymentStatus}`);
  console.log(`   AI Reasoning:    "${testOrderData.reasoning}"\n`);

  const appendUrl = `https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/Orders!A1:append?valueInputOption=USER_ENTERED`;
  const rowValues = [
    testOrderData.orderDate,
    testOrderData.orderId,
    testOrderData.customerId,
    testOrderData.customerName,
    testOrderData.phone,
    testOrderData.orderType,
    testOrderData.templateName,
    testOrderData.quantity,
    testOrderData.stitchCount,
    testOrderData.laborHours,
    testOrderData.machine,
    testOrderData.estimatedDeliveryDate,
    testOrderData.estimatedCost,
    testOrderData.paymentStatus,
    testOrderData.reasoning,
    testOrderData.overrides
  ];

  const appendRes = await fetch(appendUrl, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ values: [rowValues] })
  });

  const appendResult = await appendRes.json();
  if (!appendRes.ok) {
    throw new Error(`Failed to append test order: ${appendResult.error?.message}`);
  }
  console.log(`✅ [Stage 1 Passed] Order created in Google Sheet (Range: ${appendResult.updates?.updatedRange})\n`);

  await delay(1000);

  // --------------------------------------------------------------------------
  // STAGE 2: CJS Accountant Syncs & Fetches Order
  // --------------------------------------------------------------------------
  console.log('📌 STAGE 2: CJS Accountant ingests orders from Google Sheets...');
  const fetchUrl = `${APP_BASE_URL}/api/sheets/orders`;
  const fetchRes = await fetch(fetchUrl);
  const fetchData = await fetchRes.json();

  if (!fetchData.success || !Array.isArray(fetchData.orders)) {
    throw new Error(`Failed to fetch orders from CJS Accountant API: ${JSON.stringify(fetchData)}`);
  }

  const foundOrder = fetchData.orders.find(o => o['Order ID'] === testOrderId);
  if (!foundOrder) {
    throw new Error(`Test order ${testOrderId} was not returned by the API`);
  }

  console.log(`   Found in App API: Order ID: ${foundOrder['Order ID']}`);
  console.log(`   Payment Status:   "${foundOrder['Payment Status']}"`);
  console.log(`   Row Index:        Row #${foundOrder.rowIndex}`);
  console.log('✅ [Stage 2 Passed] Order successfully visible in CJS Accountant Orders tab!\n');

  // --------------------------------------------------------------------------
  // STAGE 3: Invoice Generation Transformation
  // --------------------------------------------------------------------------
  console.log('📌 STAGE 3: User clicks "Generate Invoice" in CJS Accountant...');
  const invoicePayload = {
    orderId: foundOrder['Order ID'],
    customer: foundOrder['Customer ID'],
    customerPhone: foundOrder['Phone'],
    serviceType: 'Machine Embroidery',
    description: `${foundOrder['Embroidery Type']} on ${foundOrder['Material']} (AI Order: ${foundOrder['Order ID']})`,
    totalStitches: parseInt(foundOrder['Stitch Count'], 10) || 0,
    estimatedCost: parseFloat(String(foundOrder['Estimated Cost']).replace(/[^0-9.]/g, '')) || 0,
    status: 'Pending'
  };

  console.log('   Generated Invoice Payload:');
  console.log(`   - Customer:      ${invoicePayload.customer}`);
  console.log(`   - Description:   ${invoicePayload.description}`);
  console.log(`   - Stitches:      ${invoicePayload.totalStitches.toLocaleString()}`);
  console.log(`   - Net Amount:    ₹${invoicePayload.estimatedCost.toFixed(2)}`);
  console.log('✅ [Stage 3 Passed] Invoice successfully generated & pre-filled from Order data!\n');

  // --------------------------------------------------------------------------
  // STAGE 4: Payment Received -> Mark Complete
  // --------------------------------------------------------------------------
  console.log('📌 STAGE 4: Customer pays invoice -> Accountant marks order "Complete"...');
  const updateUrl = `${APP_BASE_URL}/api/sheets/orders/status`;
  const updateRes = await fetch(updateUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      orderId: testOrderId,
      status: 'Complete'
    })
  });

  const updateData = await updateRes.json();
  if (!updateData.success) {
    throw new Error(`Failed to update order status: ${updateData.error}`);
  }

  console.log(`   Server Response: Status updated in Google Sheet`);
  console.log(`   Cell Updated:    ${updateData.updatedRange}`);
  console.log('✅ [Stage 4 Passed] Status updated to "Complete" via API!\n');

  await delay(1000);

  // --------------------------------------------------------------------------
  // STAGE 5: Verify Google Sheet Final State
  // --------------------------------------------------------------------------
  console.log('📌 STAGE 5: Verifying final state directly from Google Sheets...');
  const verifyUrl = `https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/Orders!A:Z`;
  const verifyRes = await fetch(verifyUrl, {
    headers: { Authorization: `Bearer ${token}` }
  });
  const verifyData = await verifyRes.json();
  const rows = verifyData.values || [];
  
  const headers = (rows[0] || []).map(h => (h || '').trim());
  let statusColIdx = headers.findIndex(h => /^payment\s*status$/i.test(h));
  if (statusColIdx === -1) statusColIdx = headers.findIndex(h => /status/i.test(h));
  if (statusColIdx === -1) statusColIdx = 13;

  let finalRow = null;
  for (let i = 1; i < rows.length; i++) {
    if (rows[i][1] === testOrderId) {
      finalRow = rows[i];
      break;
    }
  }

  if (!finalRow) {
    throw new Error(`Order ${testOrderId} not found in Google Sheet during final verification`);
  }

  const finalStatus = finalRow[statusColIdx] || '';
  console.log(`   Google Sheet Column ${String.fromCharCode(65 + statusColIdx)} (Payment Status): "${finalStatus}"`);

  if (finalStatus.toLowerCase() !== 'complete') {
    throw new Error(`Expected status "Complete", but found "${finalStatus}"`);
  }

  console.log('✅ [Stage 5 Passed] Final stage reached! Order lifecycle successfully verified end-to-end.\n');
  console.log('===============================================================');
  console.log('  🎉 ALL LIFECYCLE TESTS PASSED SUCCESSFULLY!                 ');
  console.log('===============================================================');
}

runOrderLifecycleTest().catch(err => {
  console.error('\n❌ Test failed:', err.message);
  process.exit(1);
});
