# Public assets

Files in this folder are served at the root URL.

## Logo and app name

- **Logo:** Add your logo as `logo.png` (or `logo.svg` / `logo.webp`) in this folder.  
  The app will use `/logo.png` by default.  
  To use a different path or filename, set in `.env`:

  ```
  VITE_APP_LOGO=/your-logo.svg
  ```

- **App name:** The default name is "Fuorix". To change it, set in `.env`:
  ```
  VITE_APP_NAME=Fuorix
  ```

Create a `.env` file in the `frontend` folder (same level as `package.json`) with the variables above. Restart the dev server after changing `.env`.
