#!/system/bin/sh
MODDIR=${0%/*}

# Auto-force 120Hz display refresh rate on system boot
content insert --uri content://settings/system --bind name:s:min_refresh_rate --bind value:s:120.0 2>/dev/null
content insert --uri content://settings/system --bind name:s:peak_refresh_rate --bind value:s:120.0 2>/dev/null
content insert --uri content://settings/system --bind name:s:user_refresh_rate --bind value:s:120 2>/dev/null
content insert --uri content://settings/secure --bind name:s:user_refresh_rate --bind value:s:120 2>/dev/null
content insert --uri content://settings/global --bind name:s:oplus_display_dynamic_refresh_rate --bind value:s:0 2>/dev/null
content insert --uri content://settings/global --bind name:s:oplus_display_refresh_rate --bind value:s:1 2>/dev/null
content insert --uri content://settings/system --bind name:s:oplus_customize_display_fps --bind value:s:120 2>/dev/null
echo 1 > /proc/touchpanel/game_switch_enable 2>/dev/null
echo 0 > /proc/touchpanel/oplus_tp_limit_enable 2>/dev/null
setprop debug.refresh_rate.view_override 1 2>/dev/null
