/////////////////////////////////////////////////////////////////////////////
// Author:      Vaclav Slavik
// Created:     2000/05/05
// RCS-ID:      $Id$
// Copyright:   (c) 2000 Vaclav Slavik
// Licence:     wxWindows licence
/////////////////////////////////////////////////////////////////////////////

#ifdef __GNUG__
    #pragma implementation "propedit.h"
#endif

// For compilers that support precompilation, includes "wx/wx.h".
#include "wx/wxprec.h"

#ifdef __BORLANDC__
    #pragma hdrstop
#endif

#include "wx/wx.h"
#include "wx/xml/xml.h"
#include "propframe.h"
#include "propedit.h"
#include "xmlhelpr.h"
#include "editor.h"

enum
{
    ID_CLEAR = wxID_HIGHEST + 1,
    ID_DETAILS
};



BEGIN_EVENT_TABLE(PropEditCtrl, wxPanel)
    EVT_BUTTON(ID_CLEAR, PropEditCtrl::OnButtonClear)
    EVT_BUTTON(ID_DETAILS, PropEditCtrl::OnButtonDetails)
END_EVENT_TABLE()

void PropEditCtrl::OnButtonDetails(wxCommandEvent& WXUNUSED(event))
{
    OnDetails();
}

void PropEditCtrl::OnButtonClear(wxCommandEvent& WXUNUSED(event))
{
    Clear();
    EditorFrame::Get()->NotifyChanged(CHANGED_PROPS);
}


void PropEditCtrl::BeginEdit(const wxRect& rect, wxTreeItemId ti)
{
    m_PropInfo = &(((PETreeData*)m_TreeCtrl->GetItemData(ti))->PropInfo);
    m_TreeItem = ti;

    m_CanSave = false;
    if (!m_Created)
    {
        wxSizer *sz = new wxBoxSizer(wxHORIZONTAL);
        m_TheCtrl = CreateEditCtrl();
        sz->Add(m_TheCtrl, 1);
        if (HasDetails())
            sz->Add(new wxButton(this, ID_DETAILS, _T("..."), wxDefaultPosition,
                    wxSize(16,wxDefaultCoord)));
        if (HasClearButton())
            sz->Add(new wxButton(this, ID_CLEAR, _T("X"), wxDefaultPosition,
                    wxSize(16,wxDefaultCoord)));
        SetSizer(sz);
        m_Created = true;
    }

    m_TheCtrl->SetFocus();

    SetSize(rect.x, rect.y, rect.width, rect.height);
    Show(true);
    ReadValue();
    m_CanSave = true;
}



void PropEditCtrl::EndEdit()
{
    Show(false);
}



wxTreeItemId PropEditCtrl::CreateTreeEntry(wxTreeItemId parent, const PropertyInfo& pinfo)
{
    wxTreeItemId t = m_TreeCtrl->AppendItem(parent, GetPropName(pinfo));
    m_TreeCtrl->SetItemData(t, new PETreeData(this, pinfo));
    if (IsPresent(pinfo))
        m_TreeCtrl->SetItemBold(t, true);
    return t;
}

bool PropEditCtrl::IsPresent(const PropertyInfo& pinfo)
{
    return XmlFindNode(GetNode(), pinfo.Name) != NULL;
}



void PropEditCtrl::Clear()
{
    EndEdit();

    wxXmlNode *n = XmlFindNode(GetNode(), m_PropInfo->Name);
    if (n)
    {
        n->GetParent()->RemoveChild(n);
        delete n;
        m_TreeCtrl->SetItemBold(m_TreeItem, false);
    }
}



wxString PropEditCtrl::GetValueAsText(wxTreeItemId ti)
{
    PropertyInfo& pir = ((PETreeData*)m_TreeCtrl->GetItemData(ti))->PropInfo;
    return XmlReadValue(GetNode(), pir.Name);
}

