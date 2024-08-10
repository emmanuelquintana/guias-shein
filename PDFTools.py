import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD
from PIL import Image
from pdf2image import convert_from_path
import PyPDF2
import os
import logging

# Configure logging
logging.basicConfig(filename='pdf_tools.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def select_pdf():
    pdf_file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    if pdf_file:
        convert_pdf_to_images(pdf_file)

def convert_pdf_to_images(pdf_file):
    try:
        images = convert_from_path(pdf_file)
        output_folder = filedialog.askdirectory(title="Select Output Folder")
        if output_folder:
            for i, image in enumerate(images):
                image_path = os.path.join(output_folder, f"page_{i+1}.png")
                image.save(image_path, 'PNG')
            messagebox.showinfo("Success", "PDF converted to images successfully")
            logging.info(f"Converted {pdf_file} to images in {output_folder}")
    except Exception as e:
        messagebox.showerror("Error", f"Failed to convert PDF to images: {e}")
        logging.error(f"Failed to convert PDF to images: {e}")

def merge_pdfs():
    pdf_files = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
    if pdf_files:
        output_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if output_file:
            try:
                merger = PyPDF2.PdfMerger()
                for pdf in pdf_files:
                    merger.append(pdf)
                merger.write(output_file)
                merger.close()
                messagebox.showinfo("Success", "PDF files merged successfully")
                logging.info(f"Merged {pdf_files} into {output_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to merge PDFs: {e}")
                logging.error(f"Failed to merge PDFs: {e}")

def images_to_pdf():
    image_files = filedialog.askopenfilenames(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if image_files:
        output_file = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
        if output_file:
            try:
                images = [Image.open(img) for img in image_files]
                images[0].save(output_file, save_all=True, append_images=images[1:])
                messagebox.showinfo("Success", "Images converted to PDF successfully")
                logging.info(f"Converted {image_files} to {output_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to convert images to PDF: {e}")
                logging.error(f"Failed to convert images to PDF: {e}")

def drop(event):
    files = root.tk.splitlist(event.data)
    for file in files:
        if file.lower().endswith(".pdf"):
            convert_pdf_to_images(file)
        elif file.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            images_to_pdf([file])

# Set up the main application window
root = TkinterDnD.Tk()
root.title("PDF and Image Utilities")
root.geometry("400x300")

# Create buttons for each utility
btn_select_pdf = tk.Button(root, text="Convert PDF to Images", command=select_pdf)
btn_select_pdf.pack(pady=10)

btn_merge_pdfs = tk.Button(root, text="Merge PDFs", command=merge_pdfs)
btn_merge_pdfs.pack(pady=10)

btn_images_to_pdf = tk.Button(root, text="Convert Images to PDF", command=images_to_pdf)
btn_images_to_pdf.pack(pady=10)

# Add drop target for drag and drop functionality
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', drop)

# Start the Tkinter event loop
root.mainloop()
