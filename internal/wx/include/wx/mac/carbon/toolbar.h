/////////////////////////////////////////////////////////////////////////////
// Name:        toolbar.h
// Purpose:     wxToolBar class
// Author:      Stefan Csomor
// Modified by:
// Created:     1998-01-01
// RCS-ID:      $Id$
// Copyright:   (c) Stefan Csomor
// Licence:     wxWindows licence
/////////////////////////////////////////////////////////////////////////////

#ifndef _WX_TOOLBAR_H_
#define _WX_TOOLBAR_H_

#if defined(__GNUG__) && !defined(NO_GCC_PRAGMA)
#pragma interface "toolbar.h"
#endif

#if wxUSE_TOOLBAR

#include "wx/tbarbase.h"
#include "wx/dynarray.h"

WXDLLEXPORT_DATA(extern const wxChar*) wxToolBarNameStr;

class WXDLLEXPORT wxToolBar: public wxToolBarBase
{
    DECLARE_DYNAMIC_CLASS(wxToolBar)

public:
    wxToolBar()
    {
        Init();
    }

    inline wxToolBar(
          wxWindow *parent, wxWindowID id,
          const wxPoint& pos = wxDefaultPosition, const wxSize& size = wxDefaultSize,
          long style = wxNO_BORDER | wxTB_HORIZONTAL,
          const wxString& name = wxToolBarNameStr)
    {
        Init();
        Create(parent, id, pos, size, style, name);
    }

    ~wxToolBar();

    bool Create(
          wxWindow *parent, wxWindowID id,
          const wxPoint& pos = wxDefaultPosition, const wxSize& size = wxDefaultSize,
          long style = wxNO_BORDER | wxTB_HORIZONTAL,
          const wxString& name = wxToolBarNameStr);

    // override/implement base class virtuals
    virtual bool Show(bool show = true);
    virtual bool IsShown() const;
    virtual void DoGetSize(int *width, int *height) const;
    virtual bool Realize();

    virtual void SetToolBitmapSize(const wxSize& size);
    virtual wxSize GetToolSize() const;
    virtual void SetRows(int nRows);
    virtual void SetWindowStyleFlag(long style);

    virtual wxToolBarToolBase *FindToolForPosition(wxCoord x, wxCoord y) const;

    virtual wxString MacGetToolTipString(wxPoint &where);
    virtual void MacSuperChangedPosition();

    void OnPaint(wxPaintEvent& event);
    void OnMouse(wxMouseEvent& event);

    bool MacInstallNativeToolbar(bool usesNative);
    bool MacWantsNativeToolbar();
    bool MacTopLevelHasNativeToolbar(bool *ownToolbarInstalled) const;

protected:
    // common part of all ctors
    void Init();

    // implement base class pure virtuals
    virtual bool DoInsertTool(size_t pos, wxToolBarToolBase *tool);
    virtual bool DoDeleteTool(size_t pos, wxToolBarToolBase *tool);

    virtual void DoEnableTool(wxToolBarToolBase *tool, bool enable);
    virtual void DoToggleTool(wxToolBarToolBase *tool, bool toggle);
    virtual void DoSetToggle(wxToolBarToolBase *tool, bool toggle);

    virtual wxToolBarToolBase *CreateTool(
        int id,
        const wxString& label,
        const wxBitmap& bmpNormal,
        const wxBitmap& bmpDisabled,
        wxItemKind kind,
        wxObject *clientData,
        const wxString& shortHelp,
        const wxString& longHelp);
    virtual wxToolBarToolBase *CreateTool(wxControl *control);

    DECLARE_EVENT_TABLE()

    bool m_macUsesNativeToolbar;
    void* m_macHIToolbarRef;
};

#endif // wxUSE_TOOLBAR

#endif // _WX_TOOLBAR_H_
