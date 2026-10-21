"""Native, scalable desktop styling. No webview or asset download."""
import sys
from tkinter import ttk
UI_FONT='Segoe UI' if sys.platform=='win32' else 'Helvetica'
CODE_FONT='Consolas' if sys.platform=='win32' else 'Courier'

PALETTES={
 'light':{'bg':'#F4F6FB','surface':'#FFFFFF','ink':'#172039','muted':'#77819A','line':'#E3E8F2','accent':'#6558E8','soft':'#EFEDFF','nav':'#111B32','navtext':'#A7B4CE','good':'#128970'},
 'dark':{'bg':'#131B2A','surface':'#1C283C','ink':'#EBF0FA','muted':'#9EACC3','line':'#31405B','accent':'#9587FF','soft':'#302B53','nav':'#0B1221','navtext':'#A7B4CE','good':'#54C9AC'}
}

def apply_style(root,mode='light'):
    c=PALETTES.get(mode,PALETTES['light']);style=ttk.Style(root);style.theme_use('clam')
    root.configure(bg=c['bg'])
    style.configure('.',font=(UI_FONT,10),foreground=c['ink'],background=c['bg'])
    style.configure('TFrame',background=c['bg']);style.configure('Card.TFrame',background=c['surface'])
    style.configure('TLabel',background=c['bg'],foreground=c['ink']);style.configure('Muted.TLabel',foreground=c['muted'])
    style.configure('Card.TLabel',background=c['surface']);style.configure('CardMuted.TLabel',background=c['surface'],foreground=c['muted'])
    style.configure('Title.TLabel',font=(UI_FONT,25,'bold'),foreground=c['ink'])
    style.configure('Section.TLabel',font=(UI_FONT,15,'bold'))
    style.configure('TButton',font=(UI_FONT,10),padding=(12,8),background=c['surface'],borderwidth=0,foreground=c['ink'])
    style.map('TButton',background=[('active',c['soft'])])
    style.configure('Accent.TButton',foreground='white',background=c['accent'],font=(UI_FONT,10,'bold'),padding=(18,10))
    style.map('Accent.TButton',background=[('active','#5143C7')],foreground=[('active','white')])
    style.configure('TEntry',fieldbackground=c['surface'],padding=7,bordercolor=c['line'],lightcolor=c['line'],darkcolor=c['line'])
    style.configure('TCombobox',fieldbackground=c['surface'],background=c['surface'],padding=5)
    style.configure('Treeview',rowheight=36,font=(UI_FONT,10),background=c['surface'],fieldbackground=c['surface'],foreground=c['ink'],borderwidth=0)
    style.configure('Treeview.Heading',font=(UI_FONT,9,'bold'),background=c['bg'],foreground=c['muted'],padding=(8,10),borderwidth=0)
    style.map('Treeview',background=[('selected',c['soft'])],foreground=[('selected',c['accent'])])
    style.configure('Horizontal.TProgressbar',background=c['accent'],troughcolor=c['line'],borderwidth=0)
    style.configure('TCheckbutton',background=c['bg']);style.configure('TLabelframe',background=c['bg'],bordercolor=c['line'])
    style.configure('TLabelframe.Label',font=(UI_FONT,10,'bold'))
    return c
