!macro customUnInstall
  MessageBox MB_YESNO "Also remove Savuor user data (API key, settings, and logs)?" IDNO skip
    RMDir /r "$APPDATA\Savuor"
  skip:
!macroend
