#line 1 "D:\\SVN\\telescope\\oozoo\\FW\\OnStepX\\src\\plugins\\website\\Website.cpp"
// Website plugin

#include "Website.h"
#include "Common.h"
#include "pages/Pages.h"

TaskHandle_t _webSvrTask;
void pollWebSvr(void * parameter) {
  for(;;) {
    www.handleClient();
    state.poll();
    delay(1);
  }
}

void Website::init() {
  VLF("MSG: Website Plugin");

  VLF("MSG: Set webpage handlers");
  www.on("/index.htm", []() { wifiManager.notifyAccessPointUse(); handleRoot(); });
  www.on("/index-ajax-get.txt", []() { wifiManager.notifyAccessPointUse(); indexAjaxGet(); });
  www.on("/index.txt", []() { wifiManager.notifyAccessPointUse(); indexAjax(); });

  www.on("/mount.htm", []() { wifiManager.notifyAccessPointUse(); handleMount(); });
  www.on("/mount-ajax-get.txt", []() { wifiManager.notifyAccessPointUse(); mountAjaxGet(); });
  www.on("/mount-ajax.txt", []() { wifiManager.notifyAccessPointUse(); mountAjax(); });
  www.on("/libraryHelp.htm", []() { wifiManager.notifyAccessPointUse(); handleLibraryHelp(); });

  www.on("/rotator.htm", []() { wifiManager.notifyAccessPointUse(); handleRotator(); });
  www.on("/rotator-ajax-get.txt", []() { wifiManager.notifyAccessPointUse(); rotatorAjaxGet(); });
  www.on("/rotator-ajax.txt", []() { wifiManager.notifyAccessPointUse(); rotatorAjax(); });

  www.on("/focuser.htm", []() { wifiManager.notifyAccessPointUse(); handleFocuser(); });
  www.on("/focuser-ajax-get.txt", []() { wifiManager.notifyAccessPointUse(); focuserAjaxGet(); });
  www.on("/focuser-ajax.txt", []() { wifiManager.notifyAccessPointUse(); focuserAjax(); });

  www.on("/auxiliary.htm", []() { wifiManager.notifyAccessPointUse(); handleAux(); });
  www.on("/auxiliary-ajax-get.txt", []() { wifiManager.notifyAccessPointUse(); auxAjaxGet(); });
  www.on("/auxiliary-ajax.txt", []() { wifiManager.notifyAccessPointUse(); auxAjax(); });

  www.on("/net.htm", []() { wifiManager.notifyAccessPointUse(); handleNetwork(); });

  www.on("/", []() { wifiManager.notifyAccessPointUse(); handleRoot(); });
  
  www.onNotFound([]() { wifiManager.notifyAccessPointUse(); handleNotFound(); });

  VLF("MSG: Starting port 80 web server");
  www.begin();

  // allow time for the background servers to come up
  delay(2000);

  if (status.onStepFound) {
    status.update();
    delay(100);
  }

  state.init();

  VLF("MSG: Setup, starting web server FreeRTOS task (priority 1)");
  xTaskCreatePinnedToCore(pollWebSvr,"WebSvrTask", 10000, NULL, 1, &_webSvrTask, 0);

  VLF("MSG: Website Plugin ready");
}

Website website;
