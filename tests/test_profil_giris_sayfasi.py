"""The profile scraper refuses the login page instead of reading it as a profile.

Seen 2026-09-25 on the dashboard's Profil page: the only "field" was "Beni
hatırla / Remember Me: on" — the login form's checkbox. The session had
dropped mid-run, the profile URL redirected to the login page, and every
label on it was read as a profile field, overwriting fifteen real ones
(the "profile 15 → 1" drops in earlier outages). Raising instead lets
run_sync keep the last good reading and say the section went unread.
"""
import pytest

import src.scrape_all as scrape_all


class _Surucu:
    def __init__(self, url):
        self.current_url = url
        self.istenen = []

    def get(self, url):
        self.istenen.append(url)

    def find_elements(self, by, sel):
        raise AssertionError("giriş sayfasındaki etiketler profil diye okunmamalı")


def test_giris_sayfasina_dusen_profil_okunmaz(monkeypatch):
    monkeypatch.setattr(scrape_all.time, "sleep", lambda s: None)
    surucu = _Surucu("https://portal.tedronesans.k12.tr/login?ReturnUrl=%2fpages%2fogrenci_istekler")
    with pytest.raises(RuntimeError, match="giriş sayfası"):
        scrape_all.scrape_ogrenci_profili(surucu)
