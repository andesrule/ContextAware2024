# Home Zone Analyzer

Home Zone Analyzer is a web application designed to help users find optimal residential areas in Bologna based on proximity to points of interest (POIs) and personal preferences. It uses advanced spatial analysis to calculate area scores and price clustering.

## Key Features

* Interactive Analysis:
  - Interactive map visualization
  - User preference questionnaire
  - Real-time POI visualization
  - Dynamic neighborhood radius adjustment
  - Price data visualization

* Points of Interest:
  - Schools and educational facilities
  - Parks and green areas
  - Public transportation (bus stops, train stations)
  - Healthcare facilities (hospitals, pharmacies)
  - Entertainment venues (cinemas, theaters)
  - Parking areas and electric charging stations
  - Libraries and cultural centers

* Advanced Analysis:
  - Proximity scoring for each POI category
  - Travel time calculations for different transport modes
  - Price clustering analysis using Moran's Index
  - Optimal location suggestions based on user preferences
  - Dynamic POI filtering based on travel time

## Requirements

* Docker and Docker Compose
* kubernetes 
* NodeJS


## Running with Docker 

1. Clone The Repository
2. Navigate to project directory
3. Build and Run container with the build.sh script:
```bash
chmod +x build.sh
./build.sh
```


After installation, the application will be available at http://localhost:50

## Documentation
More detailed information about the whole application can be found in Report_Context_Aware_Systems.pdf 
00

## Authors
Riccardo Benedetti and Thomas De Palma 