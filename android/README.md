# TEDY Android istemcisi

React Native projesi depo kökündeki `android/` dizinindedir. CLI özel
dizine izin verdi; kaynaklar burada, yerel Gradle projesi ise CLI'nin
ürettiği standart yerde:

- TypeScript, `package.json`: `android/`
- Uygulama kodu: `android/src/` (`shell`, `auth`, `data`, `today`, `work`,
  `assistant`, `lessons`, `books`, `more`, `theme`)
- Gradle: `android/android/` (`applicationId` / namespace `online.tedy.app`)
- Görünen ad: TEDY

iOS klasörü CLI ile geldi, derlenmez.

## Sürümler

Carbon Native Mobile örneğinin sınadığı matris kullanıldı. `@carbon/react-native`
9.0.7 peer'ları `*` olduğu için daha yeni bir React Native de kurulur; bu dilim
örnekle aynı sürümde derlenir.

| Paket | Sürüm |
| --- | --- |
| React Native | 0.79.2 |
| React | 19.0.0 |
| `@carbon/react-native` | 9.0.7 |
| `@carbon/themes` | 11.82.0 |
| `@carbon/icons` | 11.89.0 |
| `@carbon/icon-helpers` | 10.83.0 |
| `react-native-svg` | 15.15.5 |
| `react-native-webview` | 13.17.0 |
| `react-native-safe-area-context` | 5.10.1 |
| `@react-native-google-signin/google-signin` | 16.1.5 |
| `@react-native-async-storage/async-storage` | 2.2.0 |

JDK 21. Android SDK kullanıcı dizininde: `$HOME/Android/Sdk`
(`platforms;android-36`, güncel `build-tools;37.0.0`, `platform-tools`).
RN 0.79 şablonu `compileSdk` 35 ve `build-tools` 35.0.0 ister; ikisi de
kuruludur. `ANDROID_HOME` bu dizindir. `android/android/local.properties`
içindeki `sdk.dir` git'e girmez.

## Kur ve derle

Carbon paketlerinin `postinstall` adımı IBM telemetri çalıştırır. Her
`npm install` öncesi kapat:

```bash
export IBM_TELEMETRY_DISABLED=true
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export ANDROID_HOME="$HOME/Android/Sdk"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

cd android
npm install
printf 'sdk.dir=%s\n' "$ANDROID_HOME" > android/local.properties

npm test
cd android && ./gradlew assembleDebug
```

`tdyK_` veya asistan API anahtarı gömülmez. Oturum, `https://tedy.online`
üzerinde `POST /api/auth/login` ile alınan Flask çerezidir; sonraki
istekler elle `Cookie` başlığı taşır.

## Google oturumu — konsolda tek adım

Canlı Google girişi bu turda doğrulanmadı. Android OAuth istemcisi
`ted-asistan` projesinde açılır. `drmahirkurt@gmail.com` bu projede IAM
yetkisi taşımaz, bu yüzden istemci o hesapla `gcloud` üzerinden
oluşturulamaz.

Konsol adımı: **ted-asistan → Google Auth Platform → Android client**.
Paket adı `online.tedy.app`. Debug SHA-1:

```text
5E:8F:16:06:2E:A3:CD:2C:4A:0D:54:78:76:BA:A6:F3:8C:AB:F6:25
```

Test kullanıcısı: `drmahirkurt@gmail.com`. Uygulama kimlik jetonunun
hedef kitlesi olarak mevcut web istemci kimliğini kullanır
(`src/roles.py` içindeki `GOOGLE_CLIENT_ID`). Android istemcisi
açılmadan giriş derlenir; canlı giriş tamamlanmış sayılmaz.
