import os
import re
import stat
import ctypes
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Atributos de Windows
FILE_ATTRIBUTE_READONLY = 0x1
FILE_ATTRIBUTE_HIDDEN   = 0x2
FILE_ATTRIBUTE_SYSTEM   = 0x4

GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW
SetFileAttributesW = ctypes.windll.kernel32.SetFileAttributesW
GetFileAttributesW.restype = ctypes.c_uint32

# Excluir directorios sensibles/protegidos (regex, sin distinción de may/min)
EXCLUSIONES = [
    r'\\WindowsApps(\\|$)',
    r'\\Program Files(\\|$)',
    r'\\Program Files \(x86\)(\\|$)',
    r'\\ModifiableWindowsApps(\\|$)',
    r'\\System Volume Information(\\|$)',
    r'\\$Recycle\.Bin(\\|$)',
    r'\\Windows(\\|$)'
]

def ruta_excluida(path_norm):
    p = path_norm.lower()
    for rx in EXCLUSIONES:
        if re.search(rx, p, re.IGNORECASE):
            return True
    return False

def limpiar_atributos_windows(path):
    """Quita READONLY/HIDDEN/SYSTEM en Windows para poder borrar."""
    try:
        attrs = GetFileAttributesW(ctypes.c_wchar_p(path))
        if attrs == 0xFFFFFFFF:
            return
        new_attrs = attrs & ~(FILE_ATTRIBUTE_READONLY | FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM)
        if new_attrs != attrs:
            SetFileAttributesW(ctypes.c_wchar_p(path), new_attrs)
    except Exception:
        pass
    # Además, chmod de escritura por si acaso
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IWUSR | stat.S_IREAD | stat.S_IRUSR | stat.S_IROTH | stat.S_IRGRP)
    except Exception:
        pass

def eliminar_carpetas_vacias(ruta_base, dry_run=False):
    eliminadas, omitidas, errores = [], [], []

    for carpeta_actual, subcarpetas, archivos in os.walk(ruta_base, topdown=False):
        # Normalizamos separadores
        carpeta_norm = os.path.normpath(carpeta_actual)

        # Saltar rutas excluidas
        if ruta_excluida(carpeta_norm):
            omitidas.append((carpeta_norm, "Excluida por seguridad"))
            continue

        # Evitar borrar la ruta base misma (opcional: se puede permitir si queda vacía)
        # if os.path.normcase(carpeta_norm) == os.path.normcase(os.path.normpath(ruta_base)):
        #     continue

        # Si no hay nada dentro, intentamos eliminar
        if not subcarpetas and not archivos:
            try:
                if not dry_run:
                    limpiar_atributos_windows(carpeta_norm)
                    os.rmdir(carpeta_norm)
                eliminadas.append(carpeta_norm)
            except PermissionError as e:
                errores.append((carpeta_norm, f"Permisos: {e}"))
            except OSError as e:
                # Puede deberse a archivo oculto del sistema que no vimos por permisos
                errores.append((carpeta_norm, f"OSError: {e}"))
            except Exception as e:
                errores.append((carpeta_norm, f"Desconocido: {e}"))
        else:
            # Si contiene archivos, quizá alguno sea oculto/sistema
            # No borramos, pero anotamos si parece vacía salvo posibles archivos ocultos
            pass

    return eliminadas, omitidas, errores

def ejecutar():
    ruta = filedialog.askdirectory(title="Selecciona la carpeta base")
    if not ruta:
        return
    dry_run = var_dry.get() == 1

    eliminadas, omitidas, errores = eliminar_carpetas_vacias(ruta, dry_run=dry_run)

    resumen = []
    if eliminadas:
        accion = "Eliminaría" if dry_run else "Eliminadas"
        resumen.append(f"{accion} ({len(eliminadas)}):\n" + "\n".join(eliminadas[:200]))
        if len(eliminadas) > 200:
            resumen.append(f"... y {len(eliminadas)-200} más")
    if omitidas:
        resumen.append(f"Omitidas por seguridad ({len(omitidas)}):")
        resumen.extend([f"- {p} [{motivo}]" for p, motivo in omitidas[:50]])
        if len(omitidas) > 50:
            resumen.append(f"... y {len(omitidas)-50} más")
    if errores:
        resumen.append(f"Con errores ({len(errores)}):")
        resumen.extend([f"- {p} -> {motivo}" for p, motivo in errores[:100]])
        if len(errores) > 100:
            resumen.append(f"... y {len(errores)-100} más")

    if not resumen:
        resumen = ["No se encontraron carpetas vacías."]

    messagebox.showinfo("Resultado", "\n\n".join(resumen))

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Eliminar carpetas vacías")
    root.geometry("360x120")
    frm = ttk.Frame(root, padding=12)
    frm.pack(fill="both", expand=True)

    ttk.Label(frm, text="Selecciona una carpeta base y elimina subcarpetas vacías.").pack(anchor="w")
    var_dry = tk.IntVar(value=1)
    ttk.Checkbutton(frm, text="Dry-Run (solo mostrar, no borrar)", variable=var_dry).pack(anchor="w", pady=(6, 6))
    ttk.Button(frm, text="Elegir carpeta y ejecutar", command=ejecutar).pack(anchor="center", pady=4)

    root.mainloop()
