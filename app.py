import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION API ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante dans les Secrets.")

model = genai.GenerativeModel('gemini-2.5-flash')

def generer_pdf(data):
    # Initialisation FPDF simple
    pdf = FPDF(orientation='P', unit='mm', format='A4')
    pdf.add_page()
    
    # --- GESTION DES POLICES (SÉCURITÉ MAX) ---
    font_family = "Arial"
    euro_symbol = "EUR"
    
    try:
        # On tente d'enregistrer les deux variantes
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        font_family = "DejaVu"
        euro_symbol = "€"
    except Exception as e:
        # Si ça foire, on ne crash pas, on utilise Arial (toujours présent)
        font_family = "Arial"
        euro_symbol = "EUR"

    # --- CONTENU DU PDF ---
    # Titre
    pdf.set_font(font_family, 'B', 16)
    pdf.cell(0, 15, f"FACTURE : {data.get('nom_magasin', 'COMMERCE')}", ln=True, align='C')
    pdf.ln(5)

    # Date
    pdf.set_font(font_family, '', 10)
    pdf.cell(0, 10, f"Date : {data.get('date', 'N/A')}", ln=True, align='R')
    pdf.ln(5)

    # En-tête Tableau
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(font_family, 'B', 11)
    pdf.cell(130, 10, " Description", border=1, fill=True)
    pdf.cell(50, 10, f"Prix TTC ({euro_symbol})", border=1, fill=True, ln=True, align='C')

    # Articles (Gestion Texte Long)
    pdf.set_font(font_family, '', 10)
    for art in data.get('articles', []):
        nom = str(art.get('nom', 'Article'))
        prix = f"{float(art.get('prix_unitaire_ttc', 0)):.2f}"
        
        # On mémorise la position pour aligner le prix avec le nom (si multi-ligne)
        x = pdf.get_x()
        y = pdf.get_y()
        
        # Nom de l'article (MultiCell pour le texte long)
        pdf.multi_cell(130, 8, nom, border=1)
        new_y = pdf.get_y()
        h = new_y - y # Hauteur calculée
        
        # Cellule du Prix
        pdf.set_xy(x + 130, y)
        pdf.cell(50, h, prix, border=1, ln=True, align='R')

    # Totaux
    pdf.ln(10)
    total_ttc = sum(float(a.get('prix_unitaire_ttc', 0)) for a in data.get('articles', []))
    
    pdf.set_font(font_family, 'B', 12)
    pdf.set_x(120)
    pdf.cell(30, 10, "TOTAL TTC", border=0)
    pdf.cell(40, 10, f"{total_ttc:.2f} {euro_symbol}", border=1, align='R', fill=True)

    # Sortie binaire brute (S)
    return pdf.output(dest='S')

# --- INTERFACE ---
st.title("🧾 Scanner Pro v2.5")

file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])

if file:
    st.image(file, width=200)
    if st.button("Générer Facture"):
        try:
            with st.spinner("Analyse..."):
                img_bytes = file.getvalue()
                prompt = "Extraire JSON: nom_magasin, date, articles: [{nom, prix_unitaire_ttc}]"
                
                response = model.generate_content([
                    prompt, 
                    {"mime_type": file.type, "data": img_bytes}
                ])
                
                # Nettoyage JSON
                txt = response.text.replace('```json', '').replace('```', '').strip()
                res = json.loads(txt)
                
                pdf_data = generer_pdf(res)
                
                if pdf_data:
                    st.success("PDF généré !")
                    st.download_button("📥 Télécharger", pdf_data, "facture.pdf", "application/pdf")
        except Exception as e:
            st.error(f"Erreur : {e}")
