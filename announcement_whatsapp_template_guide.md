# WhatsApp Template Setup for Announcements

## 📋 Template Configuration Guide

### Template Structure You Want:

```
[Header: Image]

[Body Variables]
{1} - Announcement text (free-form from operator)
{2} - Operator name / Company name  
{3} - Operator phone number

[Button - Optional]
Call operator / Visit website
```

---

## 🎯 Step-by-Step Setup in WhatsApp Business Manager

### 1. Create Template in Meta Business Manager

**Template Name:** `announcement_notification` (or your choice)

**Category:** `MARKETING` or `UTILITY`

**Language:** Select your language (e.g., English, Hindi)

**Header Type:** `IMAGE`
- Upload your announcement header image to Meta
- This will be a fixed image URL that Meta provides

**Body Text Example:**
```
{{1}}

────────────────

{{2}}
{{3}}
```

**Variables Explanation:**
- `{{1}}` = Announcement message (free-form text from operator)
- `{{2}}` = Company name
- `{{3}}` = Operator phone number

**Button (Optional):**
- Type: `PHONE_NUMBER`
- Text: "Call Us"
- Phone: Your business number

OR

- Type: `URL`
- Text: "Visit Website"
- URL: Your website

---

## ⚙️ Configuration in Your System

### Step 1: Create the Template in Admin Panel

1. Login as **Admin**
2. Go to **Settings → WhatsApp Templates**
3. Click **"Create Template"**
4. Fill in the following:

**Template Details:**
```
Template Name: announcement_notification
Template Type: announcement
Status: Active
Language Code: en (or your language)
```

**Header Configuration:**
```
Header Type: image
Header Image URL: [Paste the URL from Meta after template approval]
```

**Body Variables:**
```
Select 3 variables in this order:

Variable 1: announcement_text
Variable 2: operator_name  
Variable 3: operator_phone
```

**Button Configuration (if using):**
```
Has Payment Button: No (or Yes if you want a custom button)
Button URL Variable: [Leave empty for announcements]
```

---

## 🔧 Backend Integration

### Option A: Use Existing Announcement Variables

The current announcement system already stores:
- `title` - Announcement title
- `message` - Announcement free-form text
- `operator_id` - Links to operator info

You need to **add announcement-specific variables** to resolve these fields.

### Option B: Update WhatsApp Service (Recommended)

Add announcement variables to `/app/backend/services/whatsapp_service.py`:

```python
# Add to KNOWN_INVOICE_VARIABLES dict (line 60)

# ── Announcement fields (new) ──────────────────────────────────────
"announcement_title":  lambda inv, sub: inv.get("title", ""),
"announcement_text":   lambda inv, sub: inv.get("message", ""),
```

### Option C: Use Operator Variables (Already Available)

These are **already implemented** and work out of the box:
```python
"operator_name":    # Returns company_name
"operator_phone":   # Returns phone  
"operator_email":   # Returns email
"operator_address": # Returns address
"operator_owner":   # Returns owner_name
```

---

## 📝 Recommended Template Configuration

### In Admin WhatsApp Templates:

**Body Variables (in order):**
1. `announcement_text` - The free-form message from operator
2. `operator_name` - Company name
3. `operator_phone` - Contact number

### Sample Template Body (in Meta):
```
{{1}}

────────────────
📢 From: {{2}}
📞 Contact: {{3}}
```

**When sent, it will look like:**
```
We will be closed on 26th January for Republic Day. Regular services will resume on 27th.

────────────────
📢 From: ABC Cable Services
📞 Contact: 9876543210
```

---

## 🔄 Integration Flow

### Current Announcement Flow:
```
Operator creates announcement
  ↓
System stores: title, message, operator_id
  ↓
Queue WhatsApp messages with: f"*{title}*\n\n{message}"
  ↓
Send via queue processor
```

### Updated Flow (With Template):
```
Operator creates announcement
  ↓
System resolves variables:
  - announcement_text = message
  - operator_name = company_name
  - operator_phone = phone
  ↓
Send via WhatsApp Template API with variables
```

---

## 🛠️ Code Changes Needed

### 1. Update WhatsApp Service Variables

Add to `/app/backend/services/whatsapp_service.py` (line 100):

```python
# ── Announcement fields ────────────────────────────────────────────
"announcement_title":  lambda inv, sub: inv.get("title", ""),
"announcement_text":   lambda inv, sub: inv.get("message", ""),
"announcement_message": lambda inv, sub: inv.get("message", ""),  # alias
```

### 2. Update Announcement Send Logic

Modify `/app/backend/routers/operator.py` (around line 316-328) to use template instead of plain text.

**Current Code:**
```python
notification = {
    "message": f"*{data.title}*\n\n{data.message}",
}
```

**Updated Code:**
```python
# Use template if announcement_template is configured
template_settings = await _get_whatsapp_template_settings()
template_name = template_settings.get("announcement_template", "")

if template_name:
    # Send via template with variables
    # Variables will be: [message, operator_name, operator_phone]
    # Store template info in queue
    notification = {
        "template_name": template_name,
        "template_variables": {
            "announcement_text": data.message,
            "operator_name": "{operator_name}",  # Resolved later
            "operator_phone": "{operator_phone}",
        }
    }
else:
    # Fallback to plain text
    notification = {
        "message": f"*{data.title}*\n\n{data.message}",
    }
```

---

## ✅ Testing Checklist

### 1. Template Approval
- [ ] Template created in Meta Business Manager
- [ ] Template approved by Meta (24-48 hours)
- [ ] Header image URL obtained from Meta

### 2. System Configuration
- [ ] Template added in Admin → WhatsApp Templates
- [ ] Header image URL configured
- [ ] Body variables selected: announcement_text, operator_name, operator_phone
- [ ] Template set as "announcement_template" in settings

### 3. Testing
- [ ] Create test announcement
- [ ] Send to test subscriber
- [ ] Verify image displays correctly
- [ ] Verify all 3 variables populate correctly
- [ ] Verify formatting looks good

---

## 🎨 Sample Visual Layout

```
┌─────────────────────────────────┐
│   [Announcement Header Image]   │
│     (e.g., megaphone icon)      │
└─────────────────────────────────┘

We will be closed on 26th January 
for Republic Day. Regular services 
will resume on 27th January.

────────────────────────────────────
📢 From: ABC Cable Services
📞 Contact: +91 98765 43210

[Call Us Button]
```

---

## 📌 Quick Summary

**What you need to configure:**

1. **Meta Business Manager:**
   - Create template with IMAGE header + 3 body variables
   - Get approval

2. **Admin Panel → WhatsApp Templates:**
   - Template Name: `announcement_notification`
   - Header: image (paste Meta's image URL)
   - Body Variables: `announcement_text`, `operator_name`, `operator_phone`

3. **Admin Panel → WhatsApp Settings:**
   - Set "Announcement Template" = `announcement_notification`

That's it! The operator info (name, phone) will auto-populate from the operator's profile.

---

## 🆘 Need Help?

If you need me to:
- Update the code to support announcement templates
- Create a custom variable resolver
- Modify the announcement sending logic

Just let me know and I'll implement it for you!
