// wifi manager, used by the webserver and wifi serial IP
#include "WifiManager.h"

#if OPERATIONAL_MODE == WIFI

#include "../tasks/OnTask.h"
#include "../nv/Nv.h"

#if defined(ESP32)
  #include <esp_wifi.h>
#endif

#if STA_AUTO_RECONNECT == true
  void reconnectStationWrapper() { wifiManager.reconnectStation(); }
#endif

void pollStationWrapper() { wifiManager.pollStation(); }

#if defined(ESP32)
  static uint8_t lastStationDisconnectReason = 0;
  static bool wifiEventDiagnosticsRegistered = false;
  static bool wifiCountryCodeApplied = false;

  static const char *wifiAuthModeName(uint8_t authMode) {
    switch ((wifi_auth_mode_t)authMode) {
      case WIFI_AUTH_OPEN: return "OPEN";
      case WIFI_AUTH_WEP: return "WEP";
      case WIFI_AUTH_WPA_PSK: return "WPA";
      case WIFI_AUTH_WPA2_PSK: return "WPA2";
      case WIFI_AUTH_WPA_WPA2_PSK: return "WPA/WPA2";
      case WIFI_AUTH_WPA2_ENTERPRISE: return "WPA2_ENT";
      case WIFI_AUTH_WPA3_PSK: return "WPA3";
      case WIFI_AUTH_WPA2_WPA3_PSK: return "WPA2/WPA3";
      default: return "UNKNOWN";
    }
  }

  static void stationConnectedEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    (void)event;
    lastStationDisconnectReason = 0;
    VF("MSG: WiFi, Station connected CH "); V(info.wifi_sta_connected.channel);
    VF(" AUTH "); VL(wifiAuthModeName(info.wifi_sta_connected.authmode));
  }

  static void stationDisconnectedEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    (void)event;
    lastStationDisconnectReason = info.wifi_sta_disconnected.reason;
    VF("WRN: WiFi, Station disconnected reason="); V(lastStationDisconnectReason);
    VF(" "); VL(WiFi.disconnectReasonName((wifi_err_reason_t)lastStationDisconnectReason));
  }

  static void stationGotIpEvent(WiFiEvent_t event, WiFiEventInfo_t info) {
    (void)event;
    VF("MSG: WiFi, Station got IP "); VL(IPAddress(info.got_ip.ip_info.ip.addr).toString().c_str());
  }

  static void registerWifiEventDiagnostics() {
    #if STA_CONNECT_DIAGNOSTICS == true
      if (wifiEventDiagnosticsRegistered) return;
      WiFi.onEvent(stationConnectedEvent, ARDUINO_EVENT_WIFI_STA_CONNECTED);
      WiFi.onEvent(stationDisconnectedEvent, ARDUINO_EVENT_WIFI_STA_DISCONNECTED);
      WiFi.onEvent(stationGotIpEvent, ARDUINO_EVENT_WIFI_STA_GOT_IP);
      wifiEventDiagnosticsRegistered = true;
    #endif
  }

  static void applyWifiCountryCode() {
    if (wifiCountryCodeApplied) return;
    if (strlen(WIFI_COUNTRY_CODE) == 0) return;

    esp_err_t result = esp_wifi_set_country_code(WIFI_COUNTRY_CODE, true);
    if (result == ESP_OK) {
      VF("MSG: WiFi, country code "); VL(WIFI_COUNTRY_CODE);
      wifiCountryCodeApplied = true;
    } else {
      VF("WRN: WiFi, country code failed err="); VL((int)result);
    }
  }
#else
  static uint8_t lastStationDisconnectReason = 0;
  static void registerWifiEventDiagnostics() {}
  static void applyWifiCountryCode() {}
#endif

static void applyWifiPerformanceMode() {
  #if WIFI_HIGH_PERFORMANCE == ON
    #if defined(ESP32)
      WiFi.setSleep(false);
    #elif defined(ESP8266)
      WiFi.setSleepMode(WIFI_NONE_SLEEP);
    #endif
    VLF("MSG: WiFi, high performance mode");
  #endif
}

void WifiManager::updateStationAddress() {
  if (!sta->dhcpEnabled) return;

  IPAddress ip = WiFi.localIP();
  IPAddress gw = WiFi.gatewayIP();
  IPAddress sn = WiFi.subnetMask();
  ip4toip4(sta->ip, ip);
  ip4toip4(sta->gw, gw);
  ip4toip4(sta->sn, sn);
}

void WifiManager::clearStationScanTarget() {
  stationScanBssidValid = false;
  stationScanChannel = 0;
  memset(stationScanBssid, 0, sizeof(stationScanBssid));
}

// blocking variant used by the reconnect monitor task
void WifiManager::beginStationConnection() {
  prepareStationConnection();
  #if STA_CONNECT_SETTLE_MS > 0
    delay(STA_CONNECT_SETTLE_MS);
  #endif
  startStationConnection();
}

void WifiManager::prepareStationConnection() {
  WiFi.disconnect(false, false);
}

void WifiManager::startStationConnection() {
  IPAddress sta_ip = IPAddress(sta->ip);
  IPAddress sta_gw = IPAddress(sta->gw);
  IPAddress sta_sn = IPAddress(sta->sn);

  if (!sta->dhcpEnabled) WiFi.config(sta_ip, sta_gw, sta_sn);
  WiFi.setAutoReconnect(false);
  lastStationDisconnectReason = 0;

  if (stationScanBssidValid && stationScanChannel > 0) {
    char bssidText[18];
    snprintf(bssidText, sizeof(bssidText), "%02X:%02X:%02X:%02X:%02X:%02X",
             stationScanBssid[0], stationScanBssid[1], stationScanBssid[2],
             stationScanBssid[3], stationScanBssid[4], stationScanBssid[5]);
    VF("MSG: WiFi, begin Station direct CH "); V(stationScanChannel);
    VF(" BSSID "); VL(bssidText);
    WiFi.begin(sta->ssid, staPwd->password, stationScanChannel, stationScanBssid);
  } else {
    WiFi.begin(sta->ssid, staPwd->password);
  }
}

// starts an async scan for the station SSID, or skips ahead if diagnostics are off
void WifiManager::startStationScan() {
  clearStationScanTarget();

  #if defined(ESP32) && STA_CONNECT_DIAGNOSTICS == true
    VF("MSG: WiFi, scan Station SSID "); VL(sta->ssid);
    WiFi.scanNetworks(true, false, false, 150, 0, sta->ssid);
    stationStateMs = millis() + 15000UL; // scan guard timeout
    stationState = WS_SCAN_WAIT;
  #else
    stationState = WS_PREPARE;
  #endif
}

void WifiManager::processStationScan(int16_t scanCount) {
  #if defined(ESP32) && STA_CONNECT_DIAGNOSTICS == true
    int32_t bestRssi = -1000;

    if (scanCount <= 0) {
      VF("WRN: WiFi, scan found no matching SSID count="); VL(scanCount);
    } else {
      for (int16_t i = 0; i < scanCount; i++) {
        VF("MSG: WiFi, scan match CH "); V(WiFi.channel(i));
        VF(" RSSI "); V(WiFi.RSSI(i));
        VF(" AUTH "); V(wifiAuthModeName((uint8_t)WiFi.encryptionType(i)));
        VF(" BSSID "); VL(WiFi.BSSIDstr(i).c_str());

        uint8_t *bssid = WiFi.BSSID(i);
        if (bssid != nullptr && WiFi.RSSI(i) > bestRssi && WiFi.channel(i) > 0) {
          bestRssi = WiFi.RSSI(i);
          stationScanChannel = WiFi.channel(i);
          memcpy(stationScanBssid, bssid, sizeof(stationScanBssid));
          stationScanBssidValid = true;
        }
      }

      if (stationScanBssidValid) {
        VF("MSG: WiFi, selected Station CH "); V(stationScanChannel);
        VF(" RSSI "); VL(bestRssi);
      }
    }

    WiFi.scanDelete();
  #else
    (void)scanCount;
  #endif
}

bool WifiManager::init() {
  if (!active) {

    readSettings();

    setStation(stationNumber);
    registerWifiEventDiagnostics();

    #if STA_AUTO_RECONNECT == true
      stationReconnectActive = false;
      stationReconnectSuspended = false;
      stationInitialConnectComplete = false;
      stationReconnectTimeoutMs = 0;
      stationReconnectAfterMs = 0;
    #endif

    char name[32] = HOST_NAME;
    strtohostname(name);

    #if MDNS_SERVER == ON
      WiFi.hostname(name);
    #endif

    if (settings.accessPointEnabled == false && settings.stationEnabled == false) {
      VF("MSG: WiFi, re-enabling access point mode to prevent lock-out!");
      settings.accessPointEnabled = true;
    }

    // set the radio mode and bring the AP (if enabled) up right away, the
    // station association runs from a background task so booting isn't stalled
    if (settings.accessPointEnabled && settings.stationEnabled) WiFi.mode(WIFI_AP_STA); else
    if (settings.accessPointEnabled) WiFi.mode(WIFI_AP); else WiFi.mode(WIFI_STA);
    delay(100);
    applyWifiCountryCode();
    applyWifiPerformanceMode();
    #if defined(CONFIG_IDF_TARGET_ESP32S2) || defined(CONFIG_IDF_TARGET_ESP32C3)
      WiFi.setTxPower(WIFI_POWER_8_5dBm);
    #endif

    if (settings.accessPointEnabled) startAccessPoint();

    if (settings.stationEnabled) {
      VF("MSG: WiFi, starting Station for SSID "); V(sta->ssid); V(" PWD "); VL(staPwd->password);
      stationAttempt = 0;
      stationFallbackDone = settings.accessPointEnabled || !settings.stationApFallback;
      #if STA_CONNECT_BOOT_DELAY_MS > 0
        VF("MSG: WiFi, waiting before Station connect "); V(STA_CONNECT_BOOT_DELAY_MS / 1000UL); VLF("s");
        stationStateMs = millis() + STA_CONNECT_BOOT_DELAY_MS;
      #else
        stationStateMs = millis();
      #endif
      stationState = WS_BOOT_DELAY;
      VF("MSG: WiFi, start Station connect task (rate 100ms priority 7)... ");
      stationConnectHandle = tasks.add(100, 0, true, 7, pollStationWrapper, "WifiSta");
      if (stationConnectHandle) { VLF("success"); } else { VLF("FAILED!"); stationState = WS_IDLE; }
    } else {
      #if STA_AUTO_RECONNECT == true
        stationInitialConnectComplete = true;
      #endif
    }

    active = true;
    VLF("MSG: WiFi, started");

    #if MDNS_SERVER == ON && !defined(ESP8266)
      sstrcpy(name, MDNS_NAME);
      strtohostname2(name);
      if (MDNS.begin(name)) { VF("MSG: WiFi, mDNS started for "); VL(name); } else { DF("WRN: WiFi, mDNS start FAILED for "); DL(name); }
    #endif
  }

  return active;
}

bool WifiManager::startAccessPoint() {
  IPAddress ap_ip = IPAddress(settings.ap.ip);
  IPAddress ap_gw = IPAddress(settings.ap.gw);
  IPAddress ap_sn = IPAddress(settings.ap.sn);

  VF("MSG: WiFi, starting Soft AP for SSID "); V(settings.ap.ssid); V(" PWD "); V(settings.ap.pwd); V(" CH "); VL(settings.ap.channel);
  WiFi.softAPConfig(ap_ip, ap_gw, ap_sn);
  bool apStarted = WiFi.softAP(settings.ap.ssid, settings.ap.pwd, settings.ap.channel);
  if (apStarted) {
    IPAddress ip = WiFi.softAPIP();
    VF("MSG: WiFi, SoftAP IP "); VL(ip.toString().c_str());
  } else {
    DLF("WRN: WiFi, starting SoftAP failed");
  }
  return apStarted;
}

// non-blocking station connect state machine, called from the WifiSta task
void WifiManager::pollStation() {
  switch (stationState) {
    case WS_BOOT_DELAY:
      if ((long)(millis() - stationStateMs) < 0) return;
      startStationScan();
    return;

    case WS_SCAN_WAIT: {
      #if defined(ESP32) && STA_CONNECT_DIAGNOSTICS == true
        int16_t scanCount = WiFi.scanComplete();
        if (scanCount == WIFI_SCAN_RUNNING) {
          if ((long)(millis() - stationStateMs) < 0) return;
          DLF("WRN: WiFi, station scan timed out");
        } else processStationScan(scanCount);
      #endif
      stationState = WS_PREPARE;
    } return;

    case WS_PREPARE:
      prepareStationConnection();
      stationStateMs = millis() + STA_CONNECT_SETTLE_MS;
      stationState = WS_CONNECT_START;
    return;

    case WS_CONNECT_START:
      if ((long)(millis() - stationStateMs) < 0) return;
      startStationConnection();
      stationStateMs = millis() + STA_CONNECT_TIMEOUT_MS;
      stationState = WS_CONNECT_WAIT;
    return;

    case WS_CONNECT_WAIT: {
      IPAddress ip = WiFi.localIP();
      if (WiFi.status() == WL_CONNECTED && validip4(ip)) { finishStationConnect(true); return; }
      if ((long)(millis() - stationStateMs) < 0) return;

      #if defined(ESP32) && STA_CONNECT_DIAGNOSTICS == true
        VF("WRN: WiFi, Station timeout status="); V((int)WiFi.status());
        VF(" reason="); V(lastStationDisconnectReason);
        VF(" "); VL(WiFi.disconnectReasonName((wifi_err_reason_t)lastStationDisconnectReason));
      #endif

      if (stationAttempt < STA_CONNECT_RETRY_COUNT) {
        stationAttempt++;
        VF("MSG: WiFi, retry Station connect "); V(stationAttempt); VF("/"); VL(STA_CONNECT_RETRY_COUNT);
        WiFi.disconnect();
        stationStateMs = millis() + STA_CONNECT_RETRY_INTERVAL_MS;
        stationState = WS_RETRY_WAIT;
      } else finishStationConnect(false);
    } return;

    case WS_RETRY_WAIT:
      if ((long)(millis() - stationStateMs) < 0) return;
      stationState = WS_PREPARE;
    return;

    default: return;
  }
}

// wrap up the initial station connect flow, on failure optionally
// fall back to access-point + station mode and try one more round
void WifiManager::finishStationConnect(bool connected) {
  if (connected) {
    updateStationAddress();
    VF("MSG: WiFi, Station IP "); VL(WiFi.localIP().toString().c_str());
    resolveStationTarget();
  } else {
    if (!stationFallbackDone) {
      VF("MSG: WiFi, starting station failed status="); VL((int)WiFi.status());
      VLF("MSG: WiFi, switching to SoftAP+Station mode");
      stationFallbackDone = true;
      settings.accessPointEnabled = true;
      WiFi.disconnect();
      WiFi.mode(WIFI_AP_STA);
      delay(100);
      startAccessPoint();
      stationAttempt = 0;
      startStationScan();
      return; // keep the connect task running for another round
    }

    if (settings.accessPointEnabled) {
      VF("MSG: WiFi, started AP but station failed status="); VL((int)WiFi.status());
    } else {
      DF("WRN: WiFi, starting station failed status="); DL((int)WiFi.status());
      WiFi.disconnect();
    }
  }

  stationState = WS_IDLE;

  #if STA_AUTO_RECONNECT == true
    stationInitialConnectComplete = true;
    VF("MSG: WiFi, start connection check task (rate 8s priority 7)... ");
    if (tasks.add(8000, 0, true, 7, reconnectStationWrapper, "WifiChk")) { VLF("success"); } else { VLF("FAILED!"); }
  #endif

  if (stationConnectHandle) { tasks.setDurationComplete(stationConnectHandle); stationConnectHandle = 0; }
}

// optional station host name lookup to set the target IP
void WifiManager::resolveStationTarget() {
  if (!staNameLookup || strlen(sta->host) == 0) return;

  IPAddress ip;
  bool resolved = false;
  char name[32] = "";
  sstrcpy(name, sta->host);
  strtohostname(name);

  if (WiFi.hostByName(name, ip) && validip4(ip)) {
    VF("MSG: WiFi, host name "); V(name); VF(" DNS resolved to "); VL(ip.toString().c_str());
    ip4toip4(sta->target, ip);
    resolved = true;
  } else {
    VF("MSG: WiFi, host name "); V(name); VLF(" DNS resolution failed!");
    #if MDNS_CLIENT == ON && !defined(ESP8266)
      strtohostname2(name);
      ip = MDNS.queryHost(name);
      if (validip4(ip)) {
        ip4toip4(sta->target, ip);
        VF("MSG: WiFi, host name "); V(name); VF(" mDNS resolved to "); VL(ip.toString().c_str());
        resolved = true;
      } else {
        VF("MSG: WiFi, host name "); V(name); VLF(" mDNS resolution failed!");
      }
    #endif
  }

  if (!resolved && !validip4(sta->target) && validip4(sta->gw)) {
    ip4toip4(sta->target, sta->gw);
    VF("MSG: WiFi, using gateway as target "); VL(IPAddress(sta->target).toString().c_str());
  }
}

#if STA_AUTO_RECONNECT == true
  void WifiManager::reconnectStation() {
    if (!settings.stationEnabled) return;
    if (!stationInitialConnectComplete) return;
    if (stationReconnectSuspended) return;

    IPAddress ip = WiFi.localIP();
    if (WiFi.status() == WL_CONNECTED && validip4(ip)) {
      updateStationAddress();
      stationReconnectActive = false;
      stationReconnectTimeoutMs = 0;
      stationReconnectAfterMs = 0;
      return;
    }

    unsigned long now = millis();
    if (stationReconnectActive) {
      if ((long)(stationReconnectTimeoutMs - now) > 0) return;

      VF("WRN: WiFi, station reconnect timeout status="); VL((int)WiFi.status());
      WiFi.disconnect(false);
      stationReconnectActive = false;
      stationReconnectTimeoutMs = 0;
      stationReconnectAfterMs = now + STA_CONNECT_RETRY_INTERVAL_MS;
      return;
    }

    if (stationReconnectAfterMs != 0 && (long)(stationReconnectAfterMs - now) > 0) return;

    VLF("MSG: WiFi, attempting reconnect");
    WiFi.disconnect(false);
    beginStationConnection();
    stationReconnectActive = true;
    stationReconnectTimeoutMs = now + STA_CONNECT_TIMEOUT_MS;
    stationReconnectAfterMs = 0;
  }
#endif

void WifiManager::notifyAccessPointUse() {
  #if STA_AUTO_RECONNECT == true
    if (stationReconnectSuspended) return;
    if (!stationInitialConnectComplete) return;
    if (!settings.accessPointEnabled || !settings.stationEnabled) return;

    IPAddress ip = WiFi.localIP();
    if (WiFi.status() == WL_CONNECTED && validip4(ip)) return;

    #if defined(ESP32) || defined(ESP8266)
      if (WiFi.softAPgetStationNum() == 0) return;
    #endif

    VLF("MSG: WiFi, AP control active; suspending Station reconnect");
    WiFi.disconnect(false);
    stationReconnectActive = false;
    stationReconnectSuspended = true;
    stationReconnectTimeoutMs = 0;
    stationReconnectAfterMs = 0;
  #endif
}

void WifiManager::setStation(int number) {
  if (number >= 1 && number <= WifiStationCount) stationNumber = number;
  sta = &station[stationNumber - 1];
  staPwd = &stationPassword[stationNumber - 1];
}

void WifiManager::disconnect() {
  if (stationConnectHandle) { tasks.remove(stationConnectHandle); stationConnectHandle = 0; }
  stationState = WS_IDLE;
  WiFi.disconnect();
  WiFi.softAPdisconnect(true);
  #if STA_AUTO_RECONNECT == true
    stationReconnectActive = false;
    stationReconnectSuspended = false;
    stationInitialConnectComplete = true;
    stationReconnectTimeoutMs = 0;
    stationReconnectAfterMs = 0;
  #endif
  active = false;
  VLF("MSG: WiFi, disconnected");      
}

void WifiManager::readSettings() {
  if (settingsReady) return;

  #ifdef NV_WIFI_SETTINGS
    VLF("MSG: WifiManager, reading settings from NV");

    if (!nv().kv().getOrInit("WIFI_SETTINGS", settings)) { DLF("WRN: Nv, init failed for WIFI_SETTINGS"); }

    for (uint8_t i = 1; i <= WifiStationCount; i++) {
      char keyStr[24];
      snprintf(keyStr, sizeof(keyStr), "WIFI_STATION%u", i);
      if (!nv().kv().getOrInit(keyStr, station[i - 1])) { DF("WRN: Nv, init failed for "); DL(keyStr); }
      snprintf(keyStr, sizeof(keyStr), "WIFI_STATION%u_PWD", i);
      if (!nv().kv().getOrInit(keyStr, stationPassword[i - 1])) { DF("WRN: Nv, init failed for "); DL(keyStr); }
    }
  #endif

  #if DEBUG != OFF
    IPAddress ap_ip = IPAddress(settings.ap.ip);
    IPAddress ap_gw = IPAddress(settings.ap.gw);
    IPAddress ap_sn = IPAddress(settings.ap.sn);

    VF("MSG: WiFi, Master Pwd   = "); VL(settings.masterPassword);

    VF("MSG: WiFi, AP Enable    = "); VL(settings.accessPointEnabled);
    VF("MSG: WiFi, AP Fallback  = "); VL(settings.stationApFallback);

    VF("MSG: WiFi, AP SSID      = "); VL(settings.ap.ssid);
    VF("MSG: WiFi, AP PWD       = "); VL(settings.ap.pwd);
    VF("MSG: WiFi, AP CH        = "); VL(settings.ap.channel);
    VF("MSG: WiFi, AP IP        = "); VL(ap_ip.toString());
    VF("MSG: WiFi, AP GATEWAY   = "); VL(ap_gw.toString());
    VF("MSG: WiFi, AP SN        = "); VL(ap_sn.toString());

    int currentStationNumber = stationNumber;

    VF("MSG: WiFi, Sta Enable   = "); VL(settings.stationEnabled);

    VF("MSG: WiFi, Sta Select   = "); VL(stationNumber);

    for (int i = 1; i <= WifiStationCount; i++) {
      setStation(i);

      IPAddress sta_ip = IPAddress(sta->ip); UNUSED(sta_ip);
      IPAddress sta_gw = IPAddress(sta->gw); UNUSED(sta_gw);
      IPAddress sta_sn = IPAddress(sta->sn); UNUSED(sta_sn);
      IPAddress target = IPAddress(sta->target); UNUSED(target);

      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" SSID    = "); VL(sta->ssid);
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" PWD     = "); VL(staPwd->password);
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" DHCP En = "); VL(sta->dhcpEnabled);
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" IP      = "); VL(sta_ip.toString());
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" GATEWAY = "); VL(sta_gw.toString());
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" SN      = "); VL(sta_sn.toString());
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" NAME    = "); VL(sta->host);
      VF("MSG: WiFi, Sta"); V(stationNumber); VF(" TARGET  = "); VL(target.toString());
    }
    stationNumber = currentStationNumber;
  #endif

  settingsReady = true;
}

void WifiManager::writeSettings() {
  if (!settingsReady) return;

  #ifdef NV_WIFI_SETTINGS
    VLF("MSG: WifiManager, writing settings to NV");
    nv().kv().put("WIFI_SETTINGS", settings);

    for (uint8_t i = 1; i <= WifiStationCount; i++) {
      char keyStr[24];
      snprintf(keyStr, sizeof(keyStr), "WIFI_STATION%u", i);
      nv().kv().put(keyStr, station[i - 1]);
      snprintf(keyStr, sizeof(keyStr), "WIFI_STATION%u_PWD", i);
      nv().kv().put(keyStr, stationPassword[i - 1]);
    }
  #endif
}

WifiManager wifiManager;

#endif
