import streamlit as st
from fpdf import FPDF
import google.generativeai as genai
import json

# --- CONFIGURATION SÉCURISÉE ---
# Utilise les "Secrets" de Streamlit Cloud pour ta clé API
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("Clé API manquante. Configurez GEMINI_API_KEY dans les secrets.")

model = genai.GenerativeModel('gemini-2.0-flash')

# --- FONCTION GENERATION PDF (MÉTHODE UNICODE) ---
def generer_pdf(data):
    pdf = FPDF()
    pdf.add_page()
    
    # CHARGEMENT DE LA POLICE UNICODE depuis le dossier fonts/
    try:
        pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf')
        pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans-Bold.ttf')
        font_name = 'DejaVu'
        use_chr128 = False
    except:
        # Repli sur Arial avec chr(128) si les fichiers sont absents
        font_name = 'Arial'
        use_chr128 = True
    
    # En-tête
    pdf.set_font(font_name, 'B', 16)
    pdf.cell(0, 10, f"FACTURE : {data['nom_magasin']}", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font(font_name, '', 12)
    pdf.cell(0, 10, f"Date: {data['date']}", 0, 1)
    pdf.ln(5)

    # Tableau
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(100, 10, "Article", 1, 0, 'L', True)
    pdf.cell(40, 10, "Prix TTC", 1, 1, 'R', True)

    # Symbole euro
    euro = chr(128) if use_chr128 else "€"
    
    pdf.set_font(font_name, '', 12)
    for art in data['articles']:
        pdf.cell(100, 10, art['nom'], 1)
        pdf.cell(40, 10, f"{art['prix_unitaire_ttc']:.2f} {euro}", 1, 1, 'R')

    pdf.ln(5)
    
    # Totaux
    pdf.cell(100, 10, "TOTAL HT", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_ht']:.2f} {euro}", 1, 1, 'R')
    
    pdf.cell(100, 10, f"TVA ({data['taux_tva']}%)", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_tva']:.2f} {euro}", 1, 1, 'R')
    
    pdf.set_font(font_name, 'B', 12)
    pdf.cell(100, 10, "TOTAL TTC", 0, 0, 'R')
    pdf.cell(40, 10, f"{data['total_ttc']:.2f} {euro}", 1, 1, 'R')
    
    # Gestion du retour selon la police utilisée
    if use_chr128:
        return pdf.output(dest='S').encode('latin-1')
    else:
        return pdf.output(dest='S')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Scanner de Tickets Pro", page_icon="🧾")
st.title("🧾 Convertisseur Ticket en Facture")
st.write("Téléchargez une photo de votre ticket, l'IA s'occupe du reste.")

fichier_image = st.file_uploader("Choisissez une photo de ticket (JPG, PNG)", type=['jpg', 'jpeg', 'png'])

if fichier_image is not None:
    st.image(fichier_image, caption="Ticket téléchargé", width=300)
    
    if st.button("Analyser et Générer la Facture"):
        with st.spinner("L'IA analyse les montants et la TVA..."):
            try:
                # 1. Préparation de l'image pour Gemini
                img_bytes = fichier_image.getvalue()
                
                # 2. Appel réel à Gemini (Prompt optimisé)
                prompt = """Analyse ce ticket de caisse. 
                Retourne UNIQUEMENT un objet JSON avec cette structure :
                {
                  "nom_magasin": "string",
                  "date": "string",
                  "taux_tva": float,
                  "articles": [{"nom": "string", "prix_unitaire_ttc": float}],
                  "total_ht": float,
                  "total_tva": float,
                  "total_ttc": float
                }"""
                
                # Correction de l'envoi d'image (format liste pour Gemini)
                response = model.generate_content([prompt, {"mime_type": "image/jpeg", "data": img_bytes}])
                
                # Nettoyage de la réponse pour extraire le JSON
                texte_reponse = response.text.replace('```json', '').replace('```', '').strip()
                resultats_ia = json.loads(texte_reponse)
                
                # 3. Génération du PDF
                pdf_output = generer_pdf(resultats_ia)
                
                st.success("Analyse terminée !")
                st.download_button(
                    label="📥 Télécharger la Facture PDF",
                    data=pdf_output,
                    file_name="facture_automatique.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")
                st.info("Astuce : Vérifie que ta clé API est correcte et que le fichier DejaVuSans.ttf est bien sur GitHub.")


