import { GoogleAuth } from 'google-auth-library';

const SPREADSHEET_ID = '1w56s9NJGjoGSOoWFhLidbQ-RtrFWt8L0gnFFHx6AolA';

async function main() {
  const auth = new GoogleAuth({
    keyFile: './service-account-key.json',
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });
  const client = await auth.getClient();
  const token = await client.getAccessToken();

  const TAB_NAME = 'Description_Templates';

  console.log('Updating Description_Templates sheet with "Service Category" and "Description" columns...');

  const rows = [
    ['Service Category', 'Description', 'Template Name'],
    ['Machine Embroidery', 'Gold Zari Floral Blouse Back & Sleeves Embroidery', 'Blouse Back & Sleeves'],
    ['Machine Embroidery', 'Tussar Silk Dupatta All-Over Mirror & Threadwork', 'Silk Dupatta Work'],
    ['Machine Embroidery', 'Velvet Gown Yoke Embroidery with Metallic Cording', 'Velvet Gown Yoke'],
    ['Machine Embroidery', 'Traditional Peacock Zari Motif on Silk Fabric', 'Peacock Zari Motif'],
    ['Machine Embroidery', 'Multi-Color Floral Embroidery Running Border Work', 'Floral Border Work'],
    ['Bridal Embroidery', 'Bridal Lehenga Custom Resham & Zari Motif Work', 'Bridal Lehenga Motif'],
    ['Bridal Embroidery', 'Heavy Bridal Saree Border & Pallu Cutwork Embroidery', 'Bridal Saree Border'],
    ['Bridal Embroidery', 'Designer Wedding Gown Front Slit Resham Embroidery', 'Wedding Gown'],
    ['Kurti & Salwar', 'Kurti Neckline & Sleeve Cuffs Multi-Thread Work', 'Kurti Neck & Cuffs'],
    ['Kurti & Salwar', 'Salwar Suit Daman & Yoke Geometric Embroidery', 'Salwar Suit Daman'],
    ['Machine Embroidery Design Making', 'DST & EMB Master Digitizing for Crest / Logo', 'Master Digitizing'],
    ['Machine Embroidery Design Making', 'Vector to Embroidery Punching & Stitch Optimization', 'Vector Punching'],
    ['Uniform & Corporate', 'Corporate Polo Crest Monogram & Badge Embroidery', 'Corporate Crest'],
    ['Uniform & Corporate', 'School & College Uniform Chest Pocket Logo Embroidery', 'Uniform Pocket Logo'],
    ['Garment Alteration / Rework', 'Embroidery Patch Application & Border Replacement', 'Patch & Border Rework']
  ];

  // Overwrite range A1:C20 with updated columns
  const updateRes = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${SPREADSHEET_ID}/values/${encodeURIComponent(TAB_NAME)}!A1:C${rows.length}?valueInputOption=USER_ENTERED`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${token.token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ values: rows })
  });

  const updateData = await updateRes.json();
  if (!updateRes.ok) {
    console.error('Update failed:', updateData);
    process.exit(1);
  }

  console.log('Successfully updated Description_Templates in Google Sheets! Range:', updateData.updatedRange);
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
