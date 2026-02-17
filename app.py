import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json
import datetime
import random

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GEMINI_API_KEY dans les secrets.")

model = genai.GenerativeModel('gemini-2.5-flash')


# --- GÉNÉRATION NUMÉRO DE FACTURE ---
def generer_numero_facture():
    now = datetime.datetime.now()
    return f"FAC-{now.strftime('%Y%m')}-{random.randint(1000, 9999)}"


# --- FONCTION GENERATION PDF PROFESSIONNELLE ---
def generer_pdf(data, numero_facture):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(15, 15, 15)
    pdf.set_auto_page_break(auto=True, margin=20)

    # Police
    try:
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf')
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf')
        font = 'DejaVu'
        euro = "€"
    except:
        font = 'Arial'
        euro = chr(128)

    # ── BANDE EN-TÊTE BLEUE ──────────────────────────────────────────────────
    pdf.set_fill_color(30, 80, 160)
    pdf.rect(0, 0, 210, 28, 'F')

    pdf.set_font(font, 'B', 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(15, 7)
    pdf.cell(0, 12, "FACTURE", 0, 1, 'L')

    pdf.set_font(font, '', 10)
    pdf.set_xy(15, 17)
    pdf.cell(0, 6, f"N° {numero_facture}  |  Date : {data.get('date', datetime.date.today().strftime('%d/%m/%Y'))}", 0, 1, 'L')

    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)

    # ── BLOC VENDEUR / ACHETEUR ───────────────────────────────────────────────
    vendeur = data.get('vendeur', {})
    acheteur = data.get('acheteur', {})

    y_start = pdf.get_y()

    # Vendeur (gauche)
    pdf.set_xy(15, y_start)
    pdf.set_font(font, 'B', 9)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(85, 6, "ÉMETTEUR", 0, 1, 'L')
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font, 'B', 10)
    pdf.set_x(15)
    pdf.cell(85, 6, vendeur.get('nom', data.get('nom_magasin', 'N/A')), 0, 1, 'L')
    pdf.set_font(font, '', 9)
    for ligne in [
        vendeur.get('adresse', ''),
        vendeur.get('ville', ''),
        vendeur.get('siret', ''),
        vendeur.get('tva_intra', ''),
    ]:
        if ligne:
            pdf.set_x(15)
            pdf.cell(85, 5, ligne, 0, 1, 'L')

    # Acheteur (droite)
    pdf.set_xy(110, y_start)
    pdf.set_font(font, 'B', 9)
    pdf.set_text_color(30, 80, 160)
    pdf.cell(85, 6, "DESTINATAIRE", 0, 0, 'L')
    pdf.set_xy(110, y_start + 6)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font, 'B', 10)
    pdf.cell(85, 6, acheteur.get('nom', 'Client'), 0, 0, 'L')
    pdf.set_xy(110, y_start + 12)
    pdf.set_font(font, '', 9)
    y_ach = y_start + 12
    for ligne in [
        acheteur.get('adresse', ''),
        acheteur.get('ville', ''),
        acheteur.get('siret', ''),
    ]:
        if ligne:
            pdf.set_xy(110, y_ach)
            pdf.cell(85, 5, ligne, 0, 0, 'L')
            y_ach += 5

    pdf.set_y(max(pdf.get_y(), y_ach) + 8)

    # ── LIGNE SÉPARATRICE ─────────────────────────────────────────────────────
    pdf.set_draw_color(30, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(5)

    # ── EN-TÊTE TABLEAU ───────────────────────────────────────────────────────
    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font, 'B', 10)
    pdf.cell(15, 9, "Qté", 1, 0, 'C', True)
    pdf.cell(105, 9, "Désignation", 1, 0, 'L', True)
    pdf.cell(35, 9, f"PU TTC ({euro})", 1, 0, 'R', True)
    pdf.cell(30, 9, f"Total ({euro})", 1, 1, 'R', True)

    # ── LIGNES ARTICLES ───────────────────────────────────────────────────────
    pdf.set_text_color(0, 0, 0)
    fill = False
    for art in data.get('articles', []):
        pdf.set_fill_color(245, 248, 255) if fill else pdf.set_fill_color(255, 255, 255)

        qte = art.get('quantite', 1)
        prix_u = art.get('prix_unitaire_ttc', 0.0)
        total_ligne = qte * prix_u

        y_before = pdf.get_y()

        pdf.set_font(font, '', 9)
        pdf.cell(15, 10, str(qte), 1, 0, 'C', fill)

        x_after_qte = pdf.get_x()
        pdf.multi_cell(105, 10, art.get('nom', ''), 1, 'L', fill)
        y_after = pdf.get_y()
        hauteur = y_after - y_before

        pdf.set_xy(x_after_qte + 105, y_before)
        pdf.cell(35, hauteur, f"{prix_u:.2f}", 1, 0, 'R', fill)
        pdf.cell(30, hauteur, f"{total_ligne:.2f}", 1, 1, 'R', fill)
        pdf.set_y(y_after)

        fill = not fill

    pdf.ln(5)

    # ── BLOC TOTAUX ───────────────────────────────────────────────────────────
    pdf.set_draw_color(200, 200, 200)
    pdf.set_line_width(0.3)

    pdf.set_font(font, '', 10)
    pdf.set_x(120)
    pdf.cell(45, 8, "Sous-total HT", 0, 0, 'R')
    pdf.cell(30, 8, f"{data.get('total_ht', 0.0):.2f} {euro}", 1, 1, 'R')

    pdf.set_x(120)
    pdf.cell(45, 8, f"TVA ({data.get('taux_tva', 20)}%)", 0, 0, 'R')
    pdf.cell(30, 8, f"{data.get('total_tva', 0.0):.2f} {euro}", 1, 1, 'R')

    pdf.set_fill_color(30, 80, 160)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(font, 'B', 11)
    pdf.set_x(120)
    pdf.cell(45, 10, "TOTAL TTC", 0, 0, 'R', True)
    pdf.cell(30, 10, f"{data.get('total_ttc', 0.0):.2f} {euro}", 1, 1, 'R', True)

    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # ── MENTIONS LÉGALES ──────────────────────────────────────────────────────
    pdf.set_draw_color(30, 80, 160)
    pdf.set_line_width(0.5)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)

    pdf.set_font(font, '', 7)
    pdf.set_text_color(100, 100, 100)
    mentions = (
        "Facture générée automatiquement. "
        "TVA non applicable, art. 293 B du CGI — si micro-entrepreneur. "
        "En cas de retard de paiement, des pénalités de retard seront appliquées "
        "conformément aux articles L.441-10 et suivants du Code de commerce. "
        "Indemnité forfaitaire pour frais de recouvrement : 40 EUR."
    )
    pdf.multi_cell(0, 4, mentions, 0, 'L')

    # ── PIED DE PAGE ──────────────────────────────────────────────────────────
    pdf.set_y(-15)
    pdf.set_font(font, '', 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 5, f"Facture N° {numero_facture} — {data.get('nom_magasin', '')} — Page 1/1", 0, 0, 'C')

    if font == 'Arial':
        return pdf.output(dest='S').encode('latin-1')
    else:
        return pdf.output(dest='S')


# ── INTERFACE STREAMLIT ──────────────────────────────────────────────────────
st.set_page_config(page_title="Scanner de Tickets Pro", page_icon="🧾", layout="centered")

st.markdown("""
    <style>
        .block-container { max-width: 700px; }
        h1 { color: #1e50a0; }
    </style>
""", unsafe_allow_html=True)

st.title("🧾 Convertisseur Ticket → Facture Pro")
st.caption("Téléchargez une photo de votre ticket, l'IA génère une facture complète et professionnelle.")

fichier_image = st.file_uploader("Photo du ticket (JPG, PNG)", type=['jpg', 'jpeg', 'png'])

if fichier_image is not None:
    st.image(fichier_image, caption="Ticket téléchargé", width=280)

    if st.button("⚡ Analyser et Générer la Facture", type="primary"):
        with st.spinner("L'IA analyse votre ticket..."):
            try:
                import PIL.Image
                import io

                # Compression image
                img = PIL.Image.open(fichier_image)
                img.thumbnail((1024, 1024))
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_bytes = buffer.getvalue()

                # Prompt enrichi
                prompt = """Analyse ce ticket de caisse et retourne UNIQUEMENT un objet JSON valide, sans texte autour, avec cette structure exacte :
{
  "nom_magasin": "string",
  "date": "string (format JJ/MM/AAAA si possible)",
  "taux_tva": 20,
  "vendeur": {
    "nom": "string (nom du magasin/entreprise)",
    "adresse": "string (adresse si visible, sinon vide)",
    "ville": "string (ville + code postal si visible, sinon vide)",
    "siret": "string (SIRET si visible, sinon vide)",
    "tva_intra": "string (numéro TVA intracommunautaire si visible, sinon vide)"
  },
  "acheteur": {
    "nom": "string (nom client si visible, sinon 'Client')",
    "adresse": "string (adresse si visible, sinon vide)",
    "ville": "string (ville si visible, sinon vide)",
    "siret": "string (SIRET si visible, sinon vide)"
  },
  "articles": [
    {
      "nom": "string",
      "quantite": 1,
      "prix_unitaire_ttc": 0.00
    }
  ],
  "total_ht": 0.00,
  "total_tva": 0.00,
  "total_ttc": 0.00
}"""

                response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
                texte_reponse = response.text.replace('```json', '').replace('```', '').strip()
                resultats_ia = json.loads(texte_reponse)

                numero_facture = generer_numero_facture()
                pdf_output = generer_pdf(resultats_ia, numero_facture)

                st.success(f"✅ Facture générée — N° {numero_facture}")

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Total TTC", f"{resultats_ia.get('total_ttc', 0):.2f} €")
                with col2:
                    st.metric("Articles détectés", len(resultats_ia.get('articles', [])))

                st.download_button(
                    label="📥 Télécharger la Facture PDF",
                    data=pdf_output,
                    file_name=f"facture_{numero_facture}.pdf",
                    mime="application/pdf",
                    type="primary"
                )

            except json.JSONDecodeError:
                st.error("❌ L'IA n'a pas retourné un JSON valide. Réessayez avec une image plus nette.")
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
                import traceback
                st.code(traceback.format_exc())
