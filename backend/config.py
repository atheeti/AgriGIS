import os
from dotenv import load_dotenv

load_dotenv()

SENTINEL_HUB_CLIENT_ID = os.getenv("SENTINEL_HUB_CLIENT_ID", "")
SENTINEL_HUB_CLIENT_SECRET = os.getenv("SENTINEL_HUB_CLIENT_SECRET", "")
SENTINEL_HUB_AUTH_URL = "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token"
SENTINEL_HUB_PROCESS_URL = "https://services.sentinel-hub.com/api/v1/process"
SENTINEL_HUB_STATS_URL = "https://services.sentinel-hub.com/api/v1/statistics"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agrigis.db")

INDEX_METADATA = {
    "NDVI": {
        "full_name": "Normalized Difference Vegetation Index",
        "description": "Measures vegetation health and density",
        "min": -1, "max": 1,
        "good_range": (0.4, 1.0),
        "bands": ["B04", "B08"],
        "formula": "(NIR - RED) / (NIR + RED)",
        "colors": [
            (-1.0, "#8B0000"),
            (-0.2, "#FF4500"),
            (0.0,  "#FFFFE0"),
            (0.2,  "#ADFF2F"),
            (0.4,  "#32CD32"),
            (0.6,  "#228B22"),
            (0.8,  "#006400"),
            (1.0,  "#004000"),
        ]
    },
    "NDMI": {
        "full_name": "Normalized Difference Moisture Index",
        "description": "Indicates water content in vegetation",
        "min": -1, "max": 1,
        "good_range": (0.0, 0.6),
        "bands": ["B08", "B11"],
        "formula": "(NIR - SWIR1) / (NIR + SWIR1)",
        "colors": [
            (-1.0, "#8B4513"),
            (-0.3, "#D2691E"),
            (0.0,  "#F0E68C"),
            (0.3,  "#87CEEB"),
            (0.6,  "#1E90FF"),
            (1.0,  "#00008B"),
        ]
    },
    "EVI": {
        "full_name": "Enhanced Vegetation Index",
        "description": "Improved vegetation index with canopy correction",
        "min": -1, "max": 1,
        "good_range": (0.2, 0.8),
        "bands": ["B02", "B04", "B08"],
        "formula": "2.5 * (NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1)",
        "colors": [
            (-1.0, "#8B0000"),
            (0.0,  "#FFFFE0"),
            (0.2,  "#ADFF2F"),
            (0.5,  "#32CD32"),
            (0.8,  "#006400"),
            (1.0,  "#004000"),
        ]
    },
    "MNDWI": {
        "full_name": "Modified Normalized Difference Water Index",
        "description": "Detects open water and soil moisture",
        "min": -1, "max": 1,
        "good_range": (-0.3, 0.0),
        "bands": ["B03", "B11"],
        "formula": "(GREEN - SWIR1) / (GREEN + SWIR1)",
        "colors": [
            (-1.0, "#8B4513"),
            (-0.2, "#DEB887"),
            (0.0,  "#FFFACD"),
            (0.3,  "#87CEEB"),
            (0.7,  "#1E90FF"),
            (1.0,  "#00008B"),
        ]
    },
    "SAVI": {
        "full_name": "Soil Adjusted Vegetation Index",
        "description": "Vegetation index with soil brightness correction",
        "min": -1.5, "max": 1.5,
        "good_range": (0.2, 0.8),
        "bands": ["B04", "B08"],
        "formula": "1.5 * (NIR - RED) / (NIR + RED + 0.5)",
        "colors": [
            (-1.5, "#8B0000"),
            (0.0,  "#FFFFE0"),
            (0.3,  "#ADFF2F"),
            (0.6,  "#32CD32"),
            (1.0,  "#006400"),
            (1.5,  "#004000"),
        ]
    },
    "GNDVI": {
        "full_name": "Green Normalized Difference Vegetation Index",
        "description": "Sensitive to chlorophyll content in vegetation",
        "min": -1, "max": 1,
        "good_range": (0.3, 0.8),
        "bands": ["B03", "B08"],
        "formula": "(NIR - GREEN) / (NIR + GREEN)",
        "colors": [
            (-1.0, "#8B0000"),
            (0.0,  "#FFFACD"),
            (0.3,  "#90EE90"),
            (0.6,  "#228B22"),
            (1.0,  "#004000"),
        ]
    },
    "GCI": {
        "full_name": "Green Chlorophyll Index",
        "description": "Estimates total chlorophyll content in leaves",
        "min": 0, "max": 20,
        "good_range": (2.0, 8.0),
        "bands": ["B03", "B08"],
        "formula": "(NIR / GREEN) - 1",
        "colors": [
            (0,   "#FFFFE0"),
            (2,   "#ADFF2F"),
            (5,   "#32CD32"),
            (10,  "#228B22"),
            (15,  "#006400"),
            (20,  "#004000"),
        ]
    },
    "SIPI": {
        "full_name": "Structure Insensitive Pigment Index",
        "description": "Ratio of carotenoids to chlorophyll a",
        "min": 0, "max": 2,
        "good_range": (1.0, 1.8),
        "bands": ["B02", "B04", "B08"],
        "formula": "(NIR - BLUE) / (NIR - RED)",
        "colors": [
            (0,   "#004000"),
            (0.5, "#228B22"),
            (1.0, "#ADFF2F"),
            (1.5, "#FFD700"),
            (2.0, "#FF4500"),
        ]
    },
    "NBR": {
        "full_name": "Normalized Burn Ratio",
        "description": "Identifies burned areas and burn severity",
        "min": -1, "max": 1,
        "good_range": (0.1, 0.8),
        "bands": ["B08", "B12"],
        "formula": "(NIR - SWIR2) / (NIR + SWIR2)",
        "colors": [
            (-1.0, "#FF0000"),
            (-0.5, "#FF8C00"),
            (0.0,  "#FFFF00"),
            (0.3,  "#90EE90"),
            (0.6,  "#228B22"),
            (1.0,  "#004000"),
        ]
    },
    "MGRVI": {
        "full_name": "Modified Green Red Vegetation Index",
        "description": "Discriminates between vegetation and soil",
        "min": -1, "max": 1,
        "good_range": (0.0, 0.6),
        "bands": ["B03", "B04"],
        "formula": "(GREEN² - RED²) / (GREEN² + RED²)",
        "colors": [
            (-1.0, "#8B0000"),
            (-0.2, "#FF6347"),
            (0.0,  "#FFFACD"),
            (0.3,  "#90EE90"),
            (0.7,  "#228B22"),
            (1.0,  "#004000"),
        ]
    },
    "NDWI": {
        "full_name": "Normalized Difference Water Index",
        "description": "Detects water bodies and water content",
        "min": -1, "max": 1,
        "good_range": (-0.3, 0.0),
        "bands": ["B03", "B08"],
        "formula": "(GREEN - NIR) / (GREEN + NIR)",
        "colors": [
            (-1.0, "#8B4513"),
            (-0.3, "#F5DEB3"),
            (0.0,  "#FFFACD"),
            (0.3,  "#87CEEB"),
            (0.7,  "#1E90FF"),
            (1.0,  "#00008B"),
        ]
    },
}

INDEX_EVALSCRIPTS_VISUAL = {
    "NDVI": """//VERSION=3
function setup() { return { input: ["B04","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0,0]],[-0.2,[1,0.27,0]],[0,[1,1,0.88]],[0.2,[0.68,1,0.18]],[0.4,[0.20,0.8,0.20]],[0.6,[0.13,0.55,0.13]],[0.8,[0.0,0.39,0.0]],[1,[0,0.25,0.01]]];
function evaluatePixel(s){let v=(s.B08-s.B04)/(s.B08+s.B04+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "NDMI": """//VERSION=3
function setup() { return { input: ["B08","B11","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0.27,0.07]],[-0.3,[0.82,0.41,0.11]],[0,[0.94,0.9,0.55]],[0.3,[0.53,0.81,0.98]],[0.6,[0.12,0.56,1]],[1,[0,0,0.55]]];
function evaluatePixel(s){let v=(s.B08-s.B11)/(s.B08+s.B11+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "EVI": """//VERSION=3
function setup() { return { input: ["B02","B04","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0,0]],[0,[1,1,0.88]],[0.2,[0.68,1,0.18]],[0.5,[0.20,0.8,0.20]],[0.8,[0,0.39,0]],[1,[0,0.25,0.01]]];
function evaluatePixel(s){let v=2.5*(s.B08-s.B04)/(s.B08+6*s.B04-7.5*s.B02+1+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "MNDWI": """//VERSION=3
function setup() { return { input: ["B03","B11","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0.27,0.07]],[-0.2,[0.87,0.72,0.53]],[0,[1,0.98,0.80]],[0.3,[0.53,0.81,0.92]],[0.7,[0.12,0.56,1]],[1,[0,0,0.55]]];
function evaluatePixel(s){let v=(s.B03-s.B11)/(s.B03+s.B11+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "SAVI": """//VERSION=3
function setup() { return { input: ["B04","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1.5,[0.54,0,0]],[0,[1,1,0.88]],[0.3,[0.68,1,0.18]],[0.6,[0.20,0.8,0.20]],[1,[0,0.39,0]],[1.5,[0,0.25,0.01]]];
function evaluatePixel(s){let v=1.5*(s.B08-s.B04)/(s.B08+s.B04+0.5+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "GNDVI": """//VERSION=3
function setup() { return { input: ["B03","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0,0]],[0,[1,0.98,0.80]],[0.3,[0.56,0.93,0.56]],[0.6,[0.13,0.55,0.13]],[1,[0,0.25,0.01]]];
function evaluatePixel(s){let v=(s.B08-s.B03)/(s.B08+s.B03+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "GCI": """//VERSION=3
function setup() { return { input: ["B03","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[0,[1,1,0.88]],[2,[0.68,1,0.18]],[5,[0.20,0.8,0.20]],[10,[0.13,0.55,0.13]],[15,[0,0.39,0]],[20,[0,0.25,0.01]]];
function evaluatePixel(s){let v=(s.B08/(s.B03+1e-10))-1;v=Math.min(Math.max(v,0),20);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "SIPI": """//VERSION=3
function setup() { return { input: ["B02","B04","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[0,[0,0.25,0.01]],[0.5,[0.13,0.55,0.13]],[1,[0.68,1,0.18]],[1.5,[1,0.84,0]],[2,[1,0.27,0]]];
function evaluatePixel(s){let d=s.B08-s.B04;let v=d===0?1:(s.B08-s.B02)/d;v=Math.min(Math.max(v,0),2);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "NBR": """//VERSION=3
function setup() { return { input: ["B08","B12","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[1,0,0]],[-0.5,[1,0.55,0]],[0,[1,1,0]],[0.3,[0.56,0.93,0.56]],[0.6,[0.13,0.55,0.13]],[1,[0,0.25,0.01]]];
function evaluatePixel(s){let v=(s.B08-s.B12)/(s.B08+s.B12+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "MGRVI": """//VERSION=3
function setup() { return { input: ["B03","B04","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0,0]],[-0.2,[1,0.39,0.28]],[0,[1,0.98,0.80]],[0.3,[0.56,0.93,0.56]],[0.7,[0.13,0.55,0.13]],[1,[0,0.25,0.01]]];
function evaluatePixel(s){let g2=s.B03*s.B03,r2=s.B04*s.B04;let v=(g2-r2)/(g2+r2+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",

    "NDWI": """//VERSION=3
function setup() { return { input: ["B03","B08","dataMask"], output: { bands: 4 } }; }
const ramp=[[-1,[0.54,0.27,0.07]],[-0.3,[0.96,0.87,0.70]],[0,[1,0.98,0.80]],[0.3,[0.53,0.81,0.92]],[0.7,[0.12,0.56,1]],[1,[0,0,0.55]]];
function evaluatePixel(s){let v=(s.B03-s.B08)/(s.B03+s.B08+1e-10);let c=colorBlend(v,ramp.map(x=>x[0]),ramp.map(x=>x[1]));return[...c,s.dataMask];}""",
}

INDEX_EVALSCRIPTS_STATS = {
    "NDVI": """//VERSION=3
function setup(){return{input:[{bands:["B04","B08","dataMask"]}],output:[{id:"ndvi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{ndvi:[(s.B08-s.B04)/(s.B08+s.B04+1e-10)],dataMask:[s.dataMask]};}""",

    "NDMI": """//VERSION=3
function setup(){return{input:[{bands:["B08","B11","dataMask"]}],output:[{id:"ndmi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{ndmi:[(s.B08-s.B11)/(s.B08+s.B11+1e-10)],dataMask:[s.dataMask]};}""",

    "EVI": """//VERSION=3
function setup(){return{input:[{bands:["B02","B04","B08","dataMask"]}],output:[{id:"evi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{evi:[2.5*(s.B08-s.B04)/(s.B08+6*s.B04-7.5*s.B02+1+1e-10)],dataMask:[s.dataMask]};}""",

    "MNDWI": """//VERSION=3
function setup(){return{input:[{bands:["B03","B11","dataMask"]}],output:[{id:"mndwi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{mndwi:[(s.B03-s.B11)/(s.B03+s.B11+1e-10)],dataMask:[s.dataMask]};}""",

    "SAVI": """//VERSION=3
function setup(){return{input:[{bands:["B04","B08","dataMask"]}],output:[{id:"savi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{savi:[1.5*(s.B08-s.B04)/(s.B08+s.B04+0.5+1e-10)],dataMask:[s.dataMask]};}""",

    "GNDVI": """//VERSION=3
function setup(){return{input:[{bands:["B03","B08","dataMask"]}],output:[{id:"gndvi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{gndvi:[(s.B08-s.B03)/(s.B08+s.B03+1e-10)],dataMask:[s.dataMask]};}""",

    "GCI": """//VERSION=3
function setup(){return{input:[{bands:["B03","B08","dataMask"]}],output:[{id:"gci",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{gci:[(s.B08/(s.B03+1e-10))-1],dataMask:[s.dataMask]};}""",

    "SIPI": """//VERSION=3
function setup(){return{input:[{bands:["B02","B04","B08","dataMask"]}],output:[{id:"sipi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){let d=s.B08-s.B04;return{sipi:[Math.abs(d)<1e-10?1:(s.B08-s.B02)/d],dataMask:[s.dataMask]};}""",

    "NBR": """//VERSION=3
function setup(){return{input:[{bands:["B08","B12","dataMask"]}],output:[{id:"nbr",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{nbr:[(s.B08-s.B12)/(s.B08+s.B12+1e-10)],dataMask:[s.dataMask]};}""",

    "MGRVI": """//VERSION=3
function setup(){return{input:[{bands:["B03","B04","dataMask"]}],output:[{id:"mgrvi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){let g2=s.B03*s.B03,r2=s.B04*s.B04;return{mgrvi:[(g2-r2)/(g2+r2+1e-10)],dataMask:[s.dataMask]};}""",

    "NDWI": """//VERSION=3
function setup(){return{input:[{bands:["B03","B08","dataMask"]}],output:[{id:"ndwi",bands:1,sampleType:"FLOAT32"},{id:"dataMask",bands:1}]};}
function evaluatePixel(s){return{ndwi:[(s.B03-s.B08)/(s.B03+s.B08+1e-10)],dataMask:[s.dataMask]};}""",
}
