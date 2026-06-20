# Courier Route Web App

This version is intended for online access using Streamlit.

## Run locally
```bash
pip install streamlit pandas openpyxl geopy
streamlit run courier_route_webapp.py
```

## Deploy online
- Streamlit Community Cloud
- Render
- Railway
- Any container platform that supports Streamlit

## Files
- courier_route_webapp.py
- courier_route_mvp.py
- courier_route_mvp_package.zip

## Geocoding
- The app uses Nominatim via geopy with a custom user_agent.
- Requests are rate-limited to 1 second between calls.
- If Latitudine/Longitudine are missing, the app tries to geocode Adresa_originala automatically.

## Easier formats
- HTML is possible if you want a purely static interface, but it is harder to connect to geocoding and route optimization.
- Excel is simpler for internal use, but less convenient for online access.
- For the easiest user experience online, Streamlit is better than plain HTML or Excel.

## Interface
- Sidebar for mode selection.
- Main area for orders, couriers and generated routes.
- One-click CSV download.

## Recommended free host
- Streamlit Community Cloud is the free option.
- It requires a GitHub repo and can deploy public apps for free.

## Deploy steps
1. Create a GitHub repository.
2. Put `courier_route_webapp.py` in the repo root.
3. Add `requirements.txt` in the repo root.
4. Open Streamlit Community Cloud, sign in with GitHub.
5. Choose the repo, branch, and main file.
6. Click Deploy.

## Input column compatibility
- The app accepts Adresa_originala, Adresa, or Address as the source address column.
- If the input file uses a different name, rename it before upload.

## Column mapping
- The app now lets you map columns for order address, order client, courier name, and courier start point.
- This makes it easier to use files with different header names.

## GitHub setup
- Repository name: `courier-route-webapp`
- Root files: `courier_route_webapp.py`, `requirements.txt`, `README.md`
- Use the repository description: `Web app for automated courier route planning with fixed delivery slots, geocoding, and route balancing.`
