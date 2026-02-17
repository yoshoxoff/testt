import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json
from io import BytesIO

# --- CONFIGURATION SÉCURISÉE ---
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante dans les Secrets Streamlit.")

# Modèle Gemini 2.5
model = genai.GenerativeModel('gemini-2.5-flash') # 2.5 utilise souvent les endpoints flash/pro

def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. GESTION POLICE ULTRA-SÉCURISÉE
    font_name = 'Arial'
    euro = "EUR"
    
    try:
        # On essaie de charger la police normale
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
        font_name = 'DejaVu'
        euro = "€"
        # On essaie de charger le GRAS, si ça rate, on reste en normal
        try:
            pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf', uni=True)
        except:
            # Si le fichier Bold manque sur ton Github, on dit à FPDF d'utiliser le normal pour le gras
            pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans.ttf', uni=True)
    except Exception as e:
        st.error(f"Erreur police : {e}. Utilisation de Arial.")
        font_name = 'Arial'

    # 2. DESIGN DE LA FACTURE
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 15, f"FACTURE : {data.get('nom_magasin', 'MAGASIN')}", 0, 1, 'C')
    
    pdf.set_font(font_name, '', 10)
    pdf.cell(0, 8, f"Date : {data.get('date', 'Inconnue')}", 0, 1, 'R')
    pdf.ln(5)

    # Entête Tableau
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font(font_name, 'B', 11)
    pdf.cell(130, 10, " Description", 1, 0, 'L', True)
    pdf.cell(40, 10, "Total TTC", 1, 1, 'C', True)

    # Articles (Gestion texte long)
    pdf.set_font(font_name, '', 11)
    for art in data.get('articles', []):
        nom = str(art.get('nom', 'Article'))
        prix = f"{float(art.get('prix_unitaire_ttc', 0)):.2f} {euro}"
        
        # Hauteur dynamique pour les noms longs
        start_y = pdf.get_y()
        pdf.multi_cell(130, 8, nom, border=1)
        end_y = pdf.get_y()
        h_cell = end_y - start_y
        
        # Aligner la cellule prix
        pdf.set_xy(140, start_y)
        pdf.cell(40, h_cell, prix, border=1, ln=1, align='R')

    # Totaux
    pdf.ln(10)
    total_ttc = float(data.get('total_ttc', 0))
    # Si l'IA n'a pas renvoyé le total, on le calcule
    if total_ttc == 0:
        total_ttc = sum(float(a.get('prix_unitaire_ttc', 0)) for a in data.get('articles', []))
    
    pdf.set_font(font_name, 'B', 12)
    pdf.set_x(110)
    pdf.cell(30, 10, "TOTAL TTC", 0, 0, 'L')
    pdf.cell(40, 10, f"{total_ttc:.2f} {euro}", 1, 1, 'R', fill=True)

    # On retourne les bytes directement
    return pdf.output(dest='S')

# --- INTERFACE ---
st.set_page_config(page_title="Scanner Facture")
st.title("🧾 Convertisseur Ticket -> Facture")

fichier = st.file_uploader("Téléchargez le ticket (Image)", type=['jpg', 'png', 'jpeg'])

if fichier:
    st.image(fichier, width=250)
    
    if st.button("🚀 Analyser et Créer le PDF"):
        with st.spinner("L'IA travaille..."):
            try:
                # Appel Gemini
                img_bytes = fichier.getvalue()
                prompt = """Analyse ce ticket et renvoie UNIQUEMENT un JSON :
                {
                  "nom_magasin": "...",
                  "date": "...",
                  "articles": [{"nom": "...", "prix_unitaire_ttc": 0.0}],
                  "total_ttc": 0.0
                }"""
                
                # Correction pour Gemini 2.x
                response = model.generate_content([
                    prompt, 
                    {"mime_type": fichier.type, "data": img_bytes}
                ])
                
                # Nettoyage JSON
                json_text = response.text.replace('```json', '').replace('```', '').strip()
                data_ia = json.loads(json_text)
                
                # Génération PDF
                pdf_bytes = generer_pdf(data_ia)
                
                if pdf_bytes:
                    st.success("Facture générée avec succès !")
                    st.download_button(
                        label="📥 Télécharger la Facture PDF",
                        data=pdf_bytes,
                        file_name="facture.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Le PDF généré est vide.")

            except Exception as e:
                st.error(f"Erreur : {e}")
