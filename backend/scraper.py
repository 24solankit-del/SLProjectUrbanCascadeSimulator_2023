"""
Urban Cascade Simulator — Web Scraper
Scrapes real-time Nagpur data (weather, air quality, seismic activity)
and enriches simulation scenarios with environmental context.
"""

import json
import logging
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NagpurDataScraper:
    """
    Scrapes real-time data for Nagpur from public APIs and websites.
    Data is used to enrich infrastructure simulation scenarios.
    """

    HEADERS = {
        "User-Agent": "UrbanCascadeSim/1.0 (Academic Research; Nagpur Infrastructure Analysis)"
    }

    def __init__(self):
        self.cache = {}
        self.last_fetch = {}

    # ── Weather Data ────────────────────────────────────────────────

    def fetch_weather(self) -> dict:
        """
        Fetch current weather conditions for Nagpur from wttr.in.
        Returns structured weather data dict.
        """
        try:
            resp = requests.get(
                "https://wttr.in/Nagpur?format=j1",
                headers=self.HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current_condition", [{}])[0]
            weather_info = {
                "timestamp": datetime.now().isoformat(),
                "source": "wttr.in",
                "city": "Nagpur",
                "temp_c": current.get("temp_C", "N/A"),
                "temp_f": current.get("temp_F", "N/A"),
                "humidity": current.get("humidity", "N/A"),
                "wind_speed_kmph": current.get("windspeedKmph", "N/A"),
                "wind_dir": current.get("winddir16Point", "N/A"),
                "weather_desc": current.get("weatherDesc", [{}])[0].get("value", "N/A"),
                "feels_like_c": current.get("FeelsLikeC", "N/A"),
                "visibility_km": current.get("visibility", "N/A"),
                "pressure_mb": current.get("pressure", "N/A"),
                "precip_mm": current.get("precipMM", "N/A"),
                "uv_index": current.get("uvIndex", "N/A"),
                "cloud_cover": current.get("cloudcover", "N/A"),
                "risk_assessment": self._assess_weather_risk(current),
            }

            self.cache["weather"] = weather_info
            self.last_fetch["weather"] = datetime.now()
            return weather_info

        except requests.RequestException as e:
            logger.warning(f"Weather fetch failed: {e}")
            return self._fallback_weather()

    def _assess_weather_risk(self, current: dict) -> dict:
        """Assess weather-related infrastructure risk."""
        risk = {"level": "LOW", "factors": []}

        precip = float(current.get("precipMM", 0))
        wind = float(current.get("windspeedKmph", 0))
        humidity = float(current.get("humidity", 0))
        temp = float(current.get("temp_C", 25))

        if precip > 20:
            risk["level"] = "HIGH"
            risk["factors"].append(f"Heavy rainfall ({precip}mm) - Flood risk for Ambazari Reservoir")
        elif precip > 5:
            risk["level"] = "MODERATE"
            risk["factors"].append(f"Moderate rainfall ({precip}mm)")

        if wind > 60:
            risk["level"] = "HIGH"
            risk["factors"].append(f"High winds ({wind} km/h) - Power line damage risk")
        elif wind > 30:
            if risk["level"] != "HIGH":
                risk["level"] = "MODERATE"
            risk["factors"].append(f"Strong winds ({wind} km/h)")

        if temp > 45:
            risk["level"] = "HIGH"
            risk["factors"].append(f"Extreme heat ({temp}°C) - Power grid overload risk")
        elif temp > 40:
            if risk["level"] != "HIGH":
                risk["level"] = "MODERATE"
            risk["factors"].append(f"High temperature ({temp}°C)")

        if humidity > 90 and precip > 10:
            risk["factors"].append("High humidity with rain - Telecom equipment risk")

        if not risk["factors"]:
            risk["factors"].append("No significant weather risks detected")

        return risk

    def _fallback_weather(self) -> dict:
        """Return cached or default weather data when API is unavailable."""
        if "weather" in self.cache:
            cached = self.cache["weather"].copy()
            cached["_note"] = "Cached data - API unavailable"
            return cached

        return {
            "timestamp": datetime.now().isoformat(),
            "source": "fallback",
            "city": "Nagpur",
            "temp_c": "32",
            "humidity": "55",
            "weather_desc": "Data unavailable - using defaults",
            "risk_assessment": {"level": "UNKNOWN", "factors": ["Live data unavailable"]},
        }

    # ── Air Quality Data ────────────────────────────────────────────

    def fetch_air_quality(self) -> dict:
        """Fetch Air Quality Index for Nagpur."""
        try:
            resp = requests.get(
                "https://api.waqi.info/feed/nagpur/?token=demo",
                headers=self.HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("status") == "ok":
                aqi_data = data.get("data", {})
                aqi_info = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "WAQI",
                    "city": "Nagpur",
                    "aqi": aqi_data.get("aqi", "N/A"),
                    "dominant_pollutant": aqi_data.get("dominentpol", "N/A"),
                    "station": aqi_data.get("city", {}).get("name", "N/A"),
                    "iaqi": {
                        k: v.get("v", "N/A")
                        for k, v in aqi_data.get("iaqi", {}).items()
                    },
                    "risk_assessment": self._assess_aqi_risk(aqi_data.get("aqi", 0)),
                }
                self.cache["air_quality"] = aqi_info
                self.last_fetch["air_quality"] = datetime.now()
                return aqi_info

        except requests.RequestException as e:
            logger.warning(f"AQI fetch failed: {e}")

        return {
            "timestamp": datetime.now().isoformat(),
            "source": "fallback",
            "city": "Nagpur",
            "aqi": "N/A",
            "risk_assessment": {"level": "UNKNOWN", "factors": ["AQI data unavailable"]},
        }

    def _assess_aqi_risk(self, aqi) -> dict:
        """Assess air quality related infrastructure/health risk."""
        try:
            aqi = int(aqi)
        except (ValueError, TypeError):
            return {"level": "UNKNOWN", "factors": ["Unable to parse AQI"]}

        if aqi > 300:
            return {"level": "HAZARDOUS", "factors": [
                f"AQI {aqi} - Hazardous conditions",
                "Health infrastructure under severe strain",
                "AIIMS & GMC emergency capacity stressed",
            ]}
        elif aqi > 200:
            return {"level": "HIGH", "factors": [
                f"AQI {aqi} - Very unhealthy air",
                "Increased hospital admissions expected",
            ]}
        elif aqi > 100:
            return {"level": "MODERATE", "factors": [f"AQI {aqi} - Unhealthy for sensitive groups"]}
        else:
            return {"level": "LOW", "factors": [f"AQI {aqi} - Satisfactory air quality"]}

    # ── Seismic Data ────────────────────────────────────────────────

    def fetch_seismic_data(self) -> dict:
        """Fetch recent earthquake data near Nagpur from USGS."""
        try:
            resp = requests.get(
                "https://earthquake.usgs.gov/fdsnws/event/1/query",
                params={
                    "format": "geojson",
                    "latitude": 21.1458,
                    "longitude": 79.0882,
                    "maxradiuskm": 500,
                    "limit": 10,
                    "orderby": "time",
                },
                headers=self.HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()

            events = []
            for feature in data.get("features", []):
                props = feature.get("properties", {})
                events.append({
                    "magnitude": props.get("mag"),
                    "place": props.get("place"),
                    "time": datetime.fromtimestamp(props["time"] / 1000).isoformat() if props.get("time") else "N/A",
                    "depth_km": feature.get("geometry", {}).get("coordinates", [0, 0, 0])[2],
                    "type": props.get("type"),
                    "url": props.get("url"),
                })

            seismic_info = {
                "timestamp": datetime.now().isoformat(),
                "source": "USGS",
                "region": "500km radius from Nagpur",
                "event_count": len(events),
                "events": events,
                "risk_assessment": self._assess_seismic_risk(events),
            }

            self.cache["seismic"] = seismic_info
            self.last_fetch["seismic"] = datetime.now()
            return seismic_info

        except requests.RequestException as e:
            logger.warning(f"Seismic fetch failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "source": "fallback",
                "event_count": 0,
                "events": [],
                "risk_assessment": {"level": "UNKNOWN", "factors": ["Seismic data unavailable"]},
            }

    def _assess_seismic_risk(self, events: list) -> dict:
        """Assess seismic risk based on recent events."""
        if not events:
            return {"level": "LOW", "factors": ["No recent seismic activity within 500km"]}

        max_mag = max(e.get("magnitude", 0) or 0 for e in events)
        if max_mag >= 5.0:
            return {"level": "HIGH", "factors": [
                f"Significant earthquake (M{max_mag}) detected",
                "Infrastructure structural integrity at risk",
            ]}
        elif max_mag >= 3.0:
            return {"level": "MODERATE", "factors": [f"Minor seismic activity (M{max_mag}) detected"]}
        else:
            return {"level": "LOW", "factors": [f"Minimal seismic activity (max M{max_mag})"]}

    # ── Nagpur News Scraping ────────────────────────────────────────

    def scrape_nagpur_infrastructure_news(self) -> dict:
        """
        Scrape infrastructure-related news headlines for Nagpur
        from public news feeds.
        """
        try:
            resp = requests.get(
                "https://news.google.com/rss/search?q=Nagpur+infrastructure+OR+power+OR+water+OR+road&hl=en-IN&gl=IN&ceid=IN:en",
                headers=self.HEADERS,
                timeout=10,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")

            headlines = []
            for item in soup.find_all("item")[:15]:
                title = item.find("title")
                link = item.find("link")
                pub_date = item.find("pubdate")
                source_el = item.find("source")

                headlines.append({
                    "title": title.text.strip() if title else "N/A",
                    "link": link.next_sibling.strip() if link and link.next_sibling else "N/A",
                    "published": pub_date.text.strip() if pub_date else "N/A",
                    "source": source_el.text.strip() if source_el else "N/A",
                })

            news_info = {
                "timestamp": datetime.now().isoformat(),
                "source": "Google News RSS",
                "query": "Nagpur infrastructure/power/water/road",
                "headline_count": len(headlines),
                "headlines": headlines,
            }

            self.cache["news"] = news_info
            self.last_fetch["news"] = datetime.now()
            return news_info

        except requests.RequestException as e:
            logger.warning(f"News scrape failed: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "source": "fallback",
                "headline_count": 0,
                "headlines": [],
                "_note": "News feed unavailable",
            }

    # ── Aggregated City Data ────────────────────────────────────────

    def fetch_all_data(self) -> dict:
        """Fetch all available data sources and return aggregated result."""
        return {
            "weather": self.fetch_weather(),
            "air_quality": self.fetch_air_quality(),
            "seismic": self.fetch_seismic_data(),
            "news": self.scrape_nagpur_infrastructure_news(),
            "fetched_at": datetime.now().isoformat(),
            "overall_risk": self._compute_overall_risk(),
        }

    def _compute_overall_risk(self) -> dict:
        """Compute overall city infrastructure risk from all sources."""
        risk_levels = {"HAZARDOUS": 4, "HIGH": 3, "MODERATE": 2, "LOW": 1, "UNKNOWN": 0}
        max_risk = "LOW"
        all_factors = []

        for key in ["weather", "air_quality", "seismic"]:
            if key in self.cache:
                assessment = self.cache[key].get("risk_assessment", {})
                level = assessment.get("level", "UNKNOWN")
                if risk_levels.get(level, 0) > risk_levels.get(max_risk, 0):
                    max_risk = level
                all_factors.extend(assessment.get("factors", []))

        return {
            "overall_level": max_risk,
            "factors": all_factors,
            "recommended_scenarios": self._recommend_scenarios(max_risk),
        }

    def _recommend_scenarios(self, risk_level: str) -> list:
        """Recommend simulation scenarios based on current risk level."""
        if risk_level == "HAZARDOUS":
            return ["compound", "grid", "flood"]
        elif risk_level == "HIGH":
            return ["grid", "flood"]
        elif risk_level == "MODERATE":
            return ["flood", "cyber"]
        else:
            return ["cyber"]
