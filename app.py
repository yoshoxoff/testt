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
    return f"{now.strftime('%Y%m')}-{random.randint(1000, 9999)}"


# --- CELLULE CENTRÉE VERTICALEMENT (helper) ---
def cell_vcenter(pdf, x, y, w, h, txt, border=1, align='C', fill=False):
    """Dessine une cellule à position absolue (x,y) de taille (w,h)."""
    pdf.set_xy(x, y)
    pdf.cell(w, h, txt, border, 0, align, fill)


# --- FONCTION GENERATION PDF ---
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

    vendeur  = data.get('vendeur', {})
    acheteur = data.get('acheteur', {})
    date_str = data.get('date', datetime.date.today().strftime('%d/%m/%Y'))
    taux_tva = data.get('taux_tva', 20)

    # ── 1. INFOS VENDEUR (haut gauche) ───────────────────────────────────────
    pdf.set_xy(15, 15)
    pdf.set_font(font, 'B', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(90, 6, vendeur.get('nom', data.get('nom_magasin', 'Mon Entreprise')), 0, 1, 'L')
    pdf.set_font(font, '', 9)
    for ligne in [
        vendeur.get('adresse', ''),
        vendeur.get('ville', ''),
        vendeur.get('pays', 'France'),
        vendeur.get('email', ''),
        vendeur.get('telephone', ''),
        vendeur.get('siret', ''),
    ]:
        if ligne:
            pdf.set_x(15)
            pdf.cell(90, 5, ligne, 0, 1, 'L')

    y_after_vendeur = pdf.get_y() + 5

    # ── 2. BLOC MÉTA grisé (gauche) + DESTINATAIRE (droite) ──────────────────
    y_meta = y_after_vendeur
    lignes_meta = [
        ("Date d'émission",    date_str),
        ("Émis par",           vendeur.get('contact', vendeur.get('nom', ''))),
        ("Délai de livraison", data.get('delai_livraison', 'À réception du paiement')),
        ("Mode de livraison",  data.get('mode_livraison', '')),
        ("Modalité de paiement", data.get('modalite_paiement', '30 jours')),
    ]
    lignes_meta = [(l, v) for l, v in lignes_meta if v]
    meta_h = max(28, len(lignes_meta) * 6 + 6)

    # Rectangle gris
    pdf.set_fill_color(235, 235, 235)
    pdf.rect(15, y_meta, 95, meta_h, 'F')

    y_cur = y_meta + 4
    for label, valeur in lignes_meta:
        pdf.set_xy(17, y_cur)
        pdf.set_font(font, '', 8)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(40, 5, label, 0, 0, 'R')
        pdf.set_text_color(0, 0, 0)
        pdf.cell(2, 5, ' ', 0, 0)
        pdf.cell(50, 5, valeur, 0, 0, 'L')
        y_cur += 6

    # Destinataire (droite)
    y_dest = y_meta
    pdf.set_xy(120, y_dest)
    pdf.set_font(font, 'B', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(75, 6, "Destinataire", 0, 1, 'L')
    y_dest += 6
    pdf.set_font(font, '', 9)
    for ligne in [
        acheteur.get('entreprise', ''),
        acheteur.get('nom', 'Client'),
        acheteur.get('adresse', ''),
        acheteur.get('ville', ''),
        acheteur.get('pays', 'France'),
    ]:
        if ligne:
            pdf.set_xy(120, y_dest)
            pdf.cell(75, 5, ligne, 0, 0, 'L')
            y_dest += 5

    # ── 3. TITRE FACTURE (droite, sous destinataire) ──────────────────────────
    y_titre = max(y_meta + meta_h, y_dest) + 6
    pdf.set_xy(100, y_titre)
    pdf.set_font(font, 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(95, 8, f"Facture n\xb0{numero_facture}", 0, 0, 'R')

    pdf.set_y(y_titre + 16)

    # ── 4. TABLEAU ────────────────────────────────────────────────────────────
    col_w    = [65, 20, 20, 30, 20, 30]
    col_hdrs = [
        "Désignation des produits\nou prestations",
        "Quantité",
        "Unité",
        f"Prix unitaire HT",
        "TVA\napplicable",
        f"TOTAL HT",
    ]
    HEADER_H = 14   # hauteur fixe de l'en-tête (2 lignes de 7)
    ROW_H    = 8    # hauteur d'une ligne article

    pdf.set_draw_color(150, 150, 150)
    pdf.set_line_width(0.3)

    # En-tête : chaque colonne dessinée à position absolue
    y_th = pdf.get_y()
    pdf.set_fill_color(200, 210, 230)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font(font, 'B', 8)

    x = 15
    for i, (hdr, w) in enumerate(zip(col_hdrs, col_w)):
        pdf.set_xy(x, y_th)
        pdf.multi_cell(w, HEADER_H / 2, hdr, 1, 'C', True)
        # multi_cell avance Y : on doit dessiner les colonnes suivantes
        # depuis la même y_th donc on les repositionne
        x += w

    # Après l'en-tête, forcer Y à y_th + HEADER_H
    pdf.set_y(y_th + HEADER_H)

    # Lignes articles
    pdf.set_font(font, '', 9)
    pdf.set_text_color(0, 0, 0)
    fill = False

    for art in data.get('articles', []):
        qte     = art.get('quantite', 1)
        unite   = art.get('unite', 'pce.')
        prix_ht = art.get('prix_unitaire_ht',
                  round(art.get('prix_unitaire_ttc', 0) / (1 + taux_tva / 100), 2))
        total_ht_ligne = round(qte * prix_ht, 2)
        nom     = art.get('nom', '')

        pdf.set_fill_color(245, 248, 255) if fill else pdf.set_fill_color(255, 255, 255)

        y_row = pdf.get_y()

        # Désignation avec retour à la ligne auto
        pdf.set_xy(15, y_row)
        pdf.multi_cell(col_w[0], ROW_H, nom, 1, 'L', fill)
        y_row_end = pdf.get_y()
        row_height = y_row_end - y_row

        # Autres colonnes à hauteur dynamique
        x = 15 + col_w[0]
        vals   = [str(qte), unite, f"{prix_ht:.2f} {euro}", f"{taux_tva}%", f"{total_ht_ligne:.2f} {euro}"]
        aligns = ['C', 'C', 'R', 'C', 'R']
        for j, (v, a, w) in enumerate(zip(vals, aligns, col_w[1:])):
            cell_vcenter(pdf, x, y_row, w, row_height, v, border=1, align=a, fill=fill)
            x += w

        pdf.set_y(y_row_end)
        fill = not fill

    # Lignes vides (esthétique — minimum 4 lignes visibles)
    nb_vides = max(0, 4 - len(data.get('articles', [])))
    for _ in range(nb_vides):
        y_row = pdf.get_y()
        x = 15
        for w in col_w:
            cell_vcenter(pdf, x, y_row, w, ROW_H, '', border=1)
            x += w
        pdf.set_y(y_row + ROW_H)

    pdf.ln(5)

    # ── 5. BAS : signature gauche + totaux droite ─────────────────────────────
    y_bas = pdf.get_y()

    # Signature
    pdf.set_xy(15, y_bas)
    pdf.set_font(font, '', 8)
    pdf.set_text_color(80, 80, 80)
    offre = data.get('offre_valide', '')
    if offre:
        pdf.cell(90, 6, f"Offre valable jusqu'au {offre}", 0, 1, 'L')
    pdf.set_xy(15, pdf.get_y() + 6)
    pdf.cell(90, 6, "Signature", 0, 1, 'L')

    # Totaux
    total_ht  = data.get('total_ht', 0.0)
    total_tva = data.get('total_tva', 0.0)
    frais     = data.get('frais_port', 0.0)
    total_ttc = data.get('total_ttc', 0.0)

    pdf.set_text_color(0, 0, 0)
    y_tot = y_bas

    def ligne_total(label, valeur, bold=False):
        nonlocal y_tot
        pdf.set_xy(105, y_tot)
        pdf.set_font(font, 'B' if bold else '', 9)
        pdf.cell(55, 7, label, 0, 0, 'L')
        pdf.cell(30, 7, f"{valeur:.2f} {euro}", 0, 0, 'R')
        y_tot += 7

    ligne_total("Total HT",  total_ht)
    ligne_total("TVA",        total_tva)
    if frais:
        ligne_total("Frais de port", frais)

    # Séparateur avant TTC
    pdf.set_draw_color(0, 0, 0)
    pdf.set_line_width(0.5)
    pdf.line(105, y_tot, 195, y_tot)
    y_tot += 2
    ligne_total("Total TTC", total_ttc, bold=True)

    pdf.ln(10)

    # ── 6. MENTIONS LÉGALES ───────────────────────────────────────────────────
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(3)
    pdf.set_font(font, '', 7)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(0, 4,
        "En cas de retard de paiement, des pénalités de retard seront appliquées conformément aux articles "
        "L.441-10 et suivants du Code de commerce. Indemnité forfaitaire pour frais de recouvrement : 40 EUR. "
        "TVA non applicable, art. 293 B du CGI si micro-entrepreneur.",
        0, 'L')

    if font == 'Arial':
        return pdf.output(dest='S').encode('latin-1')
    else:
        return pdf.output(dest='S')


# ── INTERFACE STREAMLIT ───────────────────────────────────────────────────────
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

                img = PIL.Image.open(fichier_image)
                img.thumbnail((1024, 1024))
                buffer = io.BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                img_bytes = buffer.getvalue()

                prompt = """Analyse ce ticket de caisse et retourne UNIQUEMENT un objet JSON valide, sans texte autour, avec cette structure exacte :
{
  "nom_magasin": "string",
  "date": "string (format JJ/MM/AAAA)",
  "taux_tva": 20,
  "delai_livraison": "string (si visible, sinon 'À réception du paiement')",
  "mode_livraison": "string (si visible, sinon vide)",
  "modalite_paiement": "string (si visible, sinon '30 jours')",
  "offre_valide": "string (date si visible, sinon vide)",
  "frais_port": 0.00,
  "vendeur": {
    "nom": "string",
    "adresse": "string (si visible, sinon vide)",
    "ville": "string (si visible, sinon vide)",
    "pays": "France",
    "email": "string (si visible, sinon vide)",
    "telephone": "string (si visible, sinon vide)",
    "contact": "string (nom contact si visible, sinon vide)",
    "siret": "string (si visible, sinon vide)",
    "tva_intra": "string (si visible, sinon vide)"
  },
  "acheteur": {
    "entreprise": "string (si visible, sinon vide)",
    "nom": "string (nom client si visible, sinon 'Client')",
    "adresse": "string (si visible, sinon vide)",
    "ville": "string (si visible, sinon vide)",
    "pays": "France"
  },
  "articles": [
    {
      "nom": "string",
      "quantite": 1,
      "unite": "pce.",
      "prix_unitaire_ht": 0.00,
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
