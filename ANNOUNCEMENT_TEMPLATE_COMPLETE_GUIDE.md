# ✅ Announcement WhatsApp Template - Complete Implementation Guide

## 🎯 What's Been Implemented

### ✅ Backend Changes

1. **Added Announcement Variables** (`/app/backend/services/whatsapp_service.py`)
   ```python
   "announcement_title":   lambda inv, sub: inv.get("title", "")
   "announcement_text":    lambda inv, sub: inv.get("message", "")
   "announcement_message": lambda inv, sub: inv.get("message", "")  # alias
   ```

2. **Updated Announcement Sending** (`/app/backend/routers/operator.py`)
   - Now supports WhatsApp template-based announcements
   - Automatically uses template if configured
   - Falls back to plain text if no template set
   - Resolves operator variables automatically (name, phone, email)

3. **Tested Variable Resolution**
   - ✅ All variables resolve correctly
   - ✅ Operator info auto-populated
   - ✅ Announcement text properly formatted

---

## 📋 Complete Setup Guide

### Step 1: Create Template in Meta Business Manager

1. Go to: https://business.facebook.com/latest/whatsapp_manager
2. Click **"Create Message Template"**
3. Fill in the details:

**Template Information:**
```
Name: announcement_notification
Category: MARKETING (or UTILITY)
Languages: English (or your language)
```

**Header:**
```
Type: Image
Upload: Your announcement header image (e.g., megaphone, bell icon)
```

**Body Text:**
```
{{1}}

────────────────
From: {{2}}
Contact: {{3}}
```

**Buttons (Optional):**
```
Type: PHONE_NUMBER
Text: Call Us
Phone: +919999999999
```

4. Click **Submit** and wait for Meta approval (24-48 hours)
5. Once approved, **copy the image URL** that Meta provides

---

### Step 2: Add Template in Admin Panel

1. Login as **Admin**
2. Navigate to **Settings → WhatsApp Templates**
3. Click **"Create Template"**

**Fill in the form:**
```
Template Name: announcement_notification
Template Type: announcement
Header Type: image
Header Image URL: [Paste URL from Meta]
Language Code: en
Status: Active

Body Variables (in order):
1. announcement_text
2. operator_name
3. operator_phone
```

4. Click **Save**

---

### Step 3: Configure in WhatsApp Settings

1. Go to **Settings → WhatsApp Settings**
2. Find **"Announcement Template"** dropdown
3. Select: `announcement_notification`
4. Click **Save**

---

### Step 4: Test the Announcement

1. Login as **Operator**
2. Go to **Announcements** tab
3. Click **"Create Announcement"**
4. Fill in:
   ```
   Title: Test Announcement
   Message: This is a test message to verify template variables work correctly.
   ☑ Send WhatsApp Notification
   Select: All subscribers (or specific ones)
   ```
5. Click **Send**

**Expected Result:**
- WhatsApp messages sent using template
- Image header displayed
- Your message shown in body
- Company name and phone number at bottom

---

## 🔍 How It Works

### Variable Resolution Flow

```
Operator creates announcement
  ↓
System checks if template configured
  ├─ YES: Use WhatsApp template
  │   ↓
  │   Resolve variables:
  │   - announcement_text = announcement.message
  │   - operator_name = operator.company_name
  │   - operator_phone = operator.phone
  │   ↓
  │   Send via WhatsApp Template API
  │
  └─ NO: Use plain text (legacy)
      ↓
      Queue message: "*Title*\n\nMessage"
```

### Available Variables

**Announcement Variables:**
- `announcement_title` - Title of announcement
- `announcement_text` - Full message body
- `announcement_message` - Alias for announcement_text

**Operator Variables (Auto-populated):**
- `operator_name` - Company name
- `operator_phone` - Contact number
- `operator_email` - Email address
- `operator_address` - Business address
- `operator_owner` - Owner name
- `operator_gst` - GST number
- `operator_upi_id` - UPI ID
- `operator_bank_name` - Bank name
- `operator_bank_account` - Account number
- `operator_ifsc` - IFSC code

**Customer Variables:**
- `customer_name` - Subscriber name
- `customer_phone` - Subscriber phone
- `customer_email` - Subscriber email

---

## 📝 Template Examples

### Example 1: Simple Announcement
```
Template Body (Meta):
{{1}}

From: {{2}}
📞 {{3}}

Variables:
1. announcement_text
2. operator_name
3. operator_phone

Output:
We will be closed on 26th January for Republic Day.

From: ABC Cable Services
📞 9876543210
```

### Example 2: Detailed Announcement
```
Template Body (Meta):
📢 ANNOUNCEMENT

{{1}}

────────────────────
🏢 {{2}}
📞 {{3}}
✉️ {{4}}

Variables:
1. announcement_text
2. operator_name
3. operator_phone
4. operator_email

Output:
📢 ANNOUNCEMENT

We will be closed on 26th January for Republic Day.

────────────────────
🏢 ABC Cable Services
📞 9876543210
✉️ info@abccable.com
```

### Example 3: With Customer Name
```
Template Body (Meta):
Dear {{1}},

{{2}}

Regards,
{{3}}
📞 {{4}}

Variables:
1. customer_name
2. announcement_text
3. operator_name
4. operator_phone

Output:
Dear Rajesh Kumar,

We will be closed on 26th January for Republic Day.

Regards,
ABC Cable Services
📞 9876543210
```

---

## 🧪 Testing & Verification

### Test 1: Variable Resolution ✅
```bash
cd /app/backend
python3 tests/test_announcement_template.py
```

**Expected Output:**
```
✅ All announcement variables working correctly!
✓ announcement_text: 'We will be performing maintenance...'
✓ operator_name: 'Test Company'
✓ operator_phone: '9999999999'
```

### Test 2: End-to-End Flow
1. Create announcement in operator panel
2. Send to 1-2 test subscribers
3. Verify:
   - WhatsApp message received
   - Image header displays
   - All variables populated correctly
   - No errors in backend logs

---

## 🔧 Troubleshooting

### Issue 1: Template Not Found
**Symptom:** Logs show "Announcement template 'X' not found"

**Solution:**
1. Verify template exists in Admin → WhatsApp Templates
2. Check template name matches exactly
3. Ensure template status is "Active"
4. Verify announcement_template set in WhatsApp Settings

### Issue 2: Variables Not Populating
**Symptom:** Variables show as blank or {{1}}, {{2}}

**Solution:**
1. Check template body_variables array matches your needs
2. Verify operator profile has company_name and phone filled
3. Run test: `python3 tests/test_announcement_template.py`

### Issue 3: Image Not Displaying
**Symptom:** Header image missing in WhatsApp

**Solution:**
1. Verify header_image_url is set in template
2. Check URL is accessible (not localhost)
3. Ensure URL uses HTTPS
4. Re-submit template to Meta if needed

### Issue 4: Falls Back to Plain Text
**Symptom:** Receives plain text "*Title*\n\nMessage" instead of template

**Solution:**
1. Check WhatsApp config exists (platform_whatsapp in global_settings)
2. Verify announcement_template set in whatsapp_template_settings
3. Check backend logs for template lookup errors

---

## 📊 Backend Logs

To monitor announcement sending:

```bash
# Watch real-time logs
tail -f /var/log/supervisor/backend.out.log | grep -i "announcement"

# Check for errors
tail -100 /var/log/supervisor/backend.err.log | grep -i "announcement"
```

**Successful Template Send:**
```
INFO - Sent announcement via template to 9876543210
```

**Fallback to Plain Text:**
```
WARNING - Announcement template 'announcement_notification' not found, falling back to queue
```

---

## 🎨 Visual Examples

### Mobile Preview

```
┌─────────────────────────────────┐
│                                 │
│   📢                            │
│   [Announcement Header Image]   │
│                                 │
└─────────────────────────────────┘

We will be closed on 26th January 
for Republic Day. Regular services 
will resume on 27th January.

────────────────────────────────────
From: ABC Cable Services
Contact: +91 98765 43210

┌─────────────────────────────────┐
│         📞 Call Us              │
└─────────────────────────────────┘
```

---

## ✅ Checklist

Before going live:

- [ ] Template created in Meta Business Manager
- [ ] Template approved by Meta (status: APPROVED)
- [ ] Header image URL obtained and tested
- [ ] Template added in Admin Panel
- [ ] Body variables configured correctly
- [ ] Template set as "announcement_template" in settings
- [ ] Test announcement sent successfully
- [ ] Variables populate correctly
- [ ] Image displays correctly
- [ ] No errors in backend logs
- [ ] Operator profile has complete info (name, phone, email)

---

## 🚀 Ready to Use!

Your announcement system now supports:
- ✅ WhatsApp templates with images
- ✅ Automatic variable resolution
- ✅ Operator info auto-populated
- ✅ Fallback to plain text if needed
- ✅ Professional formatting

**Next Steps:**
1. Create and approve template in Meta
2. Configure in Admin Panel
3. Test with 1-2 subscribers
4. Roll out to all subscribers

Need help? Check the logs or run the test script to verify everything is working! 🎉
