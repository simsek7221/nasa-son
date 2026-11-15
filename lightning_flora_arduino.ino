#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <string.h>
#include <stdlib.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

float sicaklik = 0;
float nem = 0;
float basinc = 0;
float ruzgar = 0;
float ndvi = -1;
float toprak = -1;

int aktifSayfa = -1;
String gelenVeri = "";
unsigned long sonVeriZamani = 0;
bool veriGeldi = false;

const char* kuraklikDurumu() {
  if (toprak < 0) return "VERI YOK";
  if (toprak < 20) return "YUKSEK";
  if (toprak < 35) return "ORTA";
  return "DUSUK";
}

const char* sicaklikDurumu() {
  if (sicaklik >= 35) return "YUKSEK";
  if (sicaklik >= 30) return "ORTA";
  return "NORMAL";
}

void setup() {
  Serial.begin(9600);
  lcd.init();
  lcd.backlight();

  lcd.setCursor(0, 0);
  lcd.print("LIGHTNING FLORA");
  lcd.setCursor(0, 1);
  lcd.print("NASA DATA SYSTEM");
  delay(1800);
  lcd.clear();
}

void veriIsle(String veri) {
  char metin[150];
  veri.toCharArray(metin, sizeof(metin));
  char* parca = strtok(metin, ",");

  while (parca != NULL) {
    char* ikiNokta = strchr(parca, ':');
    if (ikiNokta != NULL) {
      *ikiNokta = '\0';
      String anahtar = String(parca);
      float deger = atof(ikiNokta + 1);

      if (anahtar == "T") sicaklik = deger;
      if (anahtar == "H") nem = deger;
      if (anahtar == "P") basinc = deger;
      if (anahtar == "W") ruzgar = deger;
      if (anahtar == "N") ndvi = deger;
      if (anahtar == "S") toprak = deger;
    }
    parca = strtok(NULL, ",");
  }

  veriGeldi = true;
  sonVeriZamani = millis();
}

void ekranGoster(int sayfa) {
  lcd.clear();

  switch (sayfa) {
    case 0:
      lcd.setCursor(0, 0);
      lcd.print("SICAKLIK:");
      lcd.print(sicaklik, 1);
      lcd.print(" C");
      lcd.setCursor(0, 1);
      lcd.print("HAVA NEMI:");
      lcd.print(nem, 0);
      lcd.print("%");
      break;

    case 1:
      lcd.setCursor(0, 0);
      lcd.print("BASINC:");
      lcd.print(basinc, 0);
      lcd.print(" hPa");
      lcd.setCursor(0, 1);
      lcd.print("RUZGAR:");
      lcd.print(ruzgar, 1);
      lcd.print(" m/s");
      break;

    case 2:
      lcd.setCursor(0, 0);
      if (ndvi < 0) {
        lcd.print("NDVI: VERI YOK");
        lcd.setCursor(0, 1);
        lcd.print("NASA MODIS GEREK");
      } else {
        lcd.print("NDVI:");
        lcd.print(ndvi, 2);
        lcd.setCursor(0, 1);
        lcd.print("BITKI SAGLIGI");
      }
      break;

    case 3:
      lcd.setCursor(0, 0);
      if (toprak < 0) {
        lcd.print("TOPRAK NEMI: YOK");
        lcd.setCursor(0, 1);
        lcd.print("NASA POWER VERI");
      } else {
        lcd.print("TOPRAK NEMI:");
        lcd.print(toprak, 1);
        lcd.print("%");
        lcd.setCursor(0, 1);
        lcd.print("DURUM:");
        lcd.print(kuraklikDurumu());
      }
      break;

    case 4:
      lcd.setCursor(0, 0);
      lcd.print("KURAKLIK:");
      lcd.print(kuraklikDurumu());
      lcd.setCursor(0, 1);
      lcd.print("SICAKLIK:");
      lcd.print(sicaklikDurumu());
      break;

    case 5:
      lcd.setCursor(0, 0);
      lcd.print("SISTEM DURUMU");
      lcd.setCursor(0, 1);
      if (veriGeldi && millis() - sonVeriZamani < 10000) {
        lcd.print("VERI: AKTIF");
      } else {
        lcd.print("VERI: BEKLENIYOR");
      }
      break;
  }
}

void loop() {
  while (Serial.available()) {
    char karakter = Serial.read();
    if (karakter == '\n') {
      if (gelenVeri.length() > 0) {
        veriIsle(gelenVeri);
        gelenVeri = "";
        if (aktifSayfa >= 0) ekranGoster(aktifSayfa);
      }
    } else if (karakter != '\r' && gelenVeri.length() < 140) {
      gelenVeri += karakter;
    }
  }

  int potDegeri = analogRead(A0);
  int yeniSayfa = map(potDegeri, 0, 1024, 0, 6);
  if (yeniSayfa < 0) yeniSayfa = 0;
  if (yeniSayfa > 5) yeniSayfa = 5;

  if (yeniSayfa != aktifSayfa) {
    aktifSayfa = yeniSayfa;
    ekranGoster(aktifSayfa);
  }

  static bool oncekiBaglanti = false;
  bool baglanti = veriGeldi && millis() - sonVeriZamani < 10000;
  if (baglanti != oncekiBaglanti) {
    oncekiBaglanti = baglanti;
    if (aktifSayfa == 5) ekranGoster(aktifSayfa);
  }
}
