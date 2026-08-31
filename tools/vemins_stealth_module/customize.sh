ui_print "**********************************************"
ui_print "  Vemins Stealth & 120Hz Display Module      "
ui_print "**********************************************"
ui_print "[+] Unlocking 120Hz refresh rate..."
ui_print "[+] Enabling dynamic anti-recording hooks..."
set_perm_recursive $MODPATH 0 0 0755 0644
set_perm $MODPATH/service.sh 0 0 0755
