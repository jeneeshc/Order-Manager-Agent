import { GoogleAuth } from 'google-auth-library';

const SPREADSHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';

async function main() {
  const auth = new GoogleAuth({
    keyFile: './service-account-key.json',
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();

  // 1. Check existing tabs
  const metaRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}`, {
    headers: { Authorization: `Bearer ${token.token}` }
  });
  const meta = await metaRes.json();
  const existingTabs = new Set(meta.sheets.map(s => s.properties.title));

  const TAB_NAME = 'Description_Templates';

  if (!existingTabs.has(TAB_NAME)) {
    console.log(`Adding sheet tab: "${TAB_NAME}"...`);
    const addRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}:batchUpdate`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        requests: [{
          addSheet: {
            properties: { title: TAB_NAME }
          }
        }]
      })
    });
    const addData = await addRes.json();
    if (!addRes.ok) {
      console.error('Failed to add tab:', addData);
      process.exit(1);
    }
    console.log(`Tab "${TAB_NAME}" created successfully.`);
  } else {
    console.log(`Tab "${TAB_NAME}" already exists.`);
  }

  // 2. Check if headers / data exist
  const checkRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/${encodeURIComponent(TAB_NAME)}!A1:C10`, {
    headers: { Authorization: `Bearer ${token.token}` }
  });
  const checkData = await checkRes.json();

  if (!checkData.values || checkData.values.length === 0) {
    console.log('Populating headers and default garment & embroidery description templates...');
    const rows = [
      ['Template Name', 'Description', 'Category'],
      ['Bridal Lehenga Motif', 'Bridal Lehenga Custom Resham & Zari Motif Work', 'Bridal Work'],
      ['Blouse Back & Sleeves', 'Gold Zari Floral Blouse Back & Sleeves Embroidery', 'Blouse Work'],
      ['Silk Dupatta Work', 'Tussar Silk Dupatta All-Over Mirror & Threadwork', 'Dupatta & Shawl'],
      ['Master Digitizing', 'DST & EMB Master Digitizing for Crest / Logo', 'Digitizing'],
      ['Velvet Gown Yoke', 'Velvet Gown Yoke Embroidery with Metallic Cording', 'Gowns & Dresses'],
      ['Kurti Neck & Cuffs', 'Kurti Neckline & Sleeve Cuffs Multi-Thread Work', 'Kurti & Salwar'],
      ['Corporate Crest / Logo', 'Corporate Polo Crest Monogram & Badge Embroidery', 'Corporate & Uniform'],
      ['Peacock Zari Motif', 'Traditional Peacock Zari Motif on Silk Fabric', 'Custom Motif'],
      ['Floral Border Work', 'Multi-Color Floral Embroidery Running Border Work', 'Borders']
    ];

    const appendRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/${encodeURIComponent(TAB_NAME)}!A1:append?valueInputOption=USER_ENTERED`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ values: rows })
    });
    const appendData = await appendRes.json();
    console.log('Default description templates seeded:', appendData.updates?.updatedRange);
  } else {
    console.log('Templates already present in tab. Total rows:', checkData.values.length);
  }
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
