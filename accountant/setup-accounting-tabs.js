import { GoogleAuth } from 'google-auth-library';

const SHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';

async function main() {
  try {
    const auth = new GoogleAuth({
      keyFile: './service-account-key.json',
      scopes: ['https://www.googleapis.com/auth/spreadsheets']
    });

    const client = await auth.getClient();
    const token = (await client.getAccessToken()).token;

    // 1. Get existing tabs
    const metaRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const meta = await metaRes.json();
    const existingTabs = new Set(meta.sheets.map(s => s.properties.title));
    console.log('Existing tabs before setup:', Array.from(existingTabs));

    const requiredTabs = {
      'Config': ['Variable Name', 'Value', 'Last Updated'],
      'Sales_Ledger': ['Date', 'Invoice ID', 'Customer', 'Service Type', 'Total Stitches', 'Labor Hrs', 'Margin %', 'Net Price', 'GST', 'Courier', 'Gross Total'],
      'Expense_Ledger': ['Date', 'Expense Category', 'Description', 'Amount', 'Payment Method'],
      'Asset_Ledger': ['Asset Name', 'Purchase Date', 'Purchase Price', 'Useful Life (Months)', 'Monthly Depreciation'],
      'Capital_Ledger': ['Date', 'Transaction Type', 'Description', 'Amount']
    };

    // Add any missing tab
    const addRequests = [];
    for (const tabName of Object.keys(requiredTabs)) {
      if (!existingTabs.has(tabName)) {
        console.log(`Adding new tab: "${tabName}"`);
        addRequests.push({
          addSheet: {
            properties: { title: tabName }
          }
        });
      } else {
        console.log(`Tab "${tabName}" already exists, keeping it untouched.`);
      }
    }

    if (addRequests.length > 0) {
      const batchRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}:batchUpdate`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ requests: addRequests })
      });
      const batchData = await batchRes.json();
      console.log('Batch update response:', batchData.replies ? 'Success' : batchData);
    }

    // Set headers for each newly created tab (or empty tab)
    for (const [tabName, headers] of Object.entries(requiredTabs)) {
      const checkRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(tabName)}!A1:Z1`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const checkData = await checkRes.json();
      if (!checkData.values || checkData.values.length === 0) {
        console.log(`Writing headers for "${tabName}"`);
        await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/${encodeURIComponent(tabName)}!A1:append?valueInputOption=USER_ENTERED`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ values: [headers] })
        });
      }
    }

    // Populate initial Config values if empty
    const configCheckRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/Config!A2:C5`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const configCheck = await configCheckRes.json();
    if (!configCheck.values || configCheck.values.length === 0) {
      console.log('Populating initial Config rows...');
      const initialConfigRows = [
        ['Cost per 1000 Stitches', '8', new Date().toISOString()],
        ['Hourly Labor Rate', '100', new Date().toISOString()],
        ['GST Rate Percent', '18', new Date().toISOString()],
        ['Studio Name', 'CJS Designs', new Date().toISOString()]
      ];
      await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SHEET_ID}/values/Config!A2:append?valueInputOption=USER_ENTERED`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ values: initialConfigRows })
      });
    }

    console.log('\nAll accounting tabs successfully verified & configured!');
  } catch (err) {
    console.error('Error:', err.message);
  }
}

main();
