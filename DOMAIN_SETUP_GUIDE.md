# 🌐 Domain Setup Guide for www.aerofpl.net

## Overview
- **Frontend**: www.aerofpl.net (React App)
- **Backend API**: api.aerofpl.net (Django REST API)

---

## Step 1: Add DNS Records in GoDaddy

### Login to GoDaddy
1. Go to https://dcc.godaddy.com/domains
2. Find **aerofpl.net** and click "DNS"
3. Scroll to "Records" section

### Delete Existing WWW Record (if needed)
- Find the existing `www` CNAME record
- Click the pencil/edit icon
- Click "Delete" to remove it

### Add These DNS Records:

#### Record 1: Frontend (www subdomain)
```
Type: CNAME
Name: www
Value: fpl-pulse-frontend.onrender.com
TTL: 600 seconds (or default)
```

#### Record 2: Backend API (api subdomain)
```
Type: CNAME
Name: api
Value: fpl-pulse-web.onrender.com
TTL: 600 seconds (or default)
```

#### Record 3: Root Domain Redirect (Optional but Recommended)
This makes `aerofpl.net` redirect to `www.aerofpl.net`:
```
Type: A
Name: @
Value: [Use GoDaddy's domain forwarding feature instead]
```
OR use GoDaddy's **Domain Forwarding**:
- Forward `aerofpl.net` → `https://www.aerofpl.net`

### Save Changes
- Click "Save" after adding each record
- DNS propagation takes 5-60 minutes

---

## Step 2: Add Custom Domains in Render

### A. Frontend Service (www.aerofpl.net)

1. Go to https://dashboard.render.com
2. Click on **fpl-pulse-frontend** service
3. Go to "Settings" tab
4. Scroll to "Custom Domain" section
5. Click "Add Custom Domain"
6. Enter: `www.aerofpl.net`
7. Click "Save"
8. Wait for SSL certificate (takes 1-5 minutes)

### B. Backend API Service (api.aerofpl.net)

1. Go to https://dashboard.render.com
2. Click on **fpl-pulse-web** service
3. Go to "Settings" tab
4. Scroll to "Custom Domain" section
5. Click "Add Custom Domain"
6. Enter: `api.aerofpl.net`
7. Click "Save"
8. Wait for SSL certificate (takes 1-5 minutes)

---

## Step 3: Deploy Updated Configuration

The configuration files have been updated. Now deploy:

```bash
cd /Users/nyashamutseta/Desktop/personal/FPL
git add render.yaml
git commit -m "Configure custom domain: www.aerofpl.net"
git push origin main
```

Render will automatically:
- Rebuild both services
- Apply new CORS settings
- Use api.aerofpl.net for API calls

---

## Step 4: Verify Everything Works

### After DNS Propagates (5-60 minutes):

1. **Check DNS**:
   ```bash
   # Check if DNS is working
   nslookup www.aerofpl.net
   nslookup api.aerofpl.net
   ```

2. **Test Frontend**:
   - Visit: https://www.aerofpl.net
   - Should show your FPL Pulse homepage
   - Check browser console for any errors

3. **Test API**:
   - Visit: https://api.aerofpl.net/api/landing/
   - Should return JSON data

4. **Test Wildcard Simulator**:
   - Visit: https://www.aerofpl.net/wildcard
   - Create a team
   - Try sharing (should use new domain in URLs)

---

## Troubleshooting

### Issue: "This site can't be reached"
**Solution**: DNS hasn't propagated yet. Wait 15-30 more minutes.

### Issue: "Not Secure" warning
**Solution**: 
- Make sure you added custom domain in Render dashboard
- Wait for SSL certificate (shows as "Verified" in Render)

### Issue: API calls failing (CORS errors)
**Solution**: 
- Make sure you deployed the updated `render.yaml`
- Check Render service logs for CORS errors
- Verify `CORS_ALLOWED_ORIGINS` includes `https://www.aerofpl.net`

### Issue: Old Render URLs still being used
**Solution**:
- Clear browser cache
- Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
- Check that frontend service rebuilt with `VITE_API_URL=https://api.aerofpl.net`

---

## Configuration Summary

### Updated Files:
- ✅ `render.yaml` - CORS, ALLOWED_HOSTS, and API URL updated

### Environment Variables Set:
```yaml
# Frontend
VITE_API_URL=https://api.aerofpl.net

# Backend
ALLOWED_HOSTS=api.aerofpl.net,fpl-pulse-web.onrender.com
CORS_ALLOWED_ORIGINS=https://www.aerofpl.net,https://aerofpl.net,https://fpl-pulse-frontend.onrender.com,https://fpl-pulse-web.onrender.com
```

### URLs After Setup:
- Frontend: https://www.aerofpl.net
- Backend API: https://api.aerofpl.net
- Wildcard Simulator: https://www.aerofpl.net/wildcard
- Dream Team: https://www.aerofpl.net/dream-team
- Admin: https://api.aerofpl.net/admin/

---

## Next Steps

1. ✅ Update DNS records in GoDaddy (see Step 1)
2. ✅ Add custom domains in Render (see Step 2)
3. ✅ Deploy configuration changes (see Step 3)
4. ⏳ Wait for DNS propagation (5-60 minutes)
5. ✅ Test your new domain!

**Questions?** Check Render dashboard logs or GoDaddy DNS management console.
