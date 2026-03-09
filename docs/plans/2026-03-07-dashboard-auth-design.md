# Dashboard Google Sign-In Auth

**Tarih:** 2026-03-07
**Amaç:** Dashboard'a sadece aile bireylerinin erişmesini sağlayan Google Sign-In.

## Yaklaşım
Google Identity Services (GIS) frontend butonu + backend token doğrulama + Flask session.

## Whitelist
- isikkurtx@gmail.com
- drmahirkurt@gmail.com
- ozlem.murzoglu@gmail.com
- huriye.murzoglu@gmail.com

## Akış
1. Login ekranı → Google Sign-In butonu
2. Google id_token → POST /api/auth/login
3. Backend doğrular + whitelist → session cookie
4. Tüm /api/* endpoint'leri session gerektirir

## Dosyalar
- Backend: `src/dashboard_api.py` (auth endpoint'leri + session middleware)
- Frontend: `dashboard/src/components/LoginPage.tsx`, `dashboard/src/hooks/useAuth.ts`, `dashboard/src/App.tsx`
