# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.15.2
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# # Geographic data I/O {#sec-read-write}
#
# ## Prerequisites {.unnumbered}
#
# This chapter requires importing the following packages:

import urllib.request
import zipfile
import numpy as np
import fiona
import geopandas as gpd
import shapely
import rasterio
import rasterio.plot
import cartopy
import osmnx as ox

#| echo: false
import pandas as pd
import matplotlib.pyplot as plt
pd.options.display.max_rows = 6
pd.options.display.max_columns = 6
pd.options.display.max_colwidth = 35
plt.rcParams['figure.figsize'] = (5, 5)

# It also relies on the following data files:

nz = gpd.read_file('data/nz.gpkg')
nz_elev = rasterio.open('data/nz_elev.tif')

# ## Introduction
#
# This chapter is about reading and writing geographic data.
# Geographic data input is essential for geocomputation: real-world applications are impossible without data.
# Data output is also vital, enabling others to use valuable new or improved datasets resulting from your work.
# Taken together, these processes of input/output can be referred to as data I/O.
#
# Geographic data I/O is often done with few lines of code at the beginning and end of projects.
# It is often overlooked as a simple one step process.
# However, mistakes made at the outset of projects (e.g., using an out-of-date or in some way faulty dataset) can lead to large problems later down the line, so it is worth putting considerable time into identifying which datasets are available, where they can be found and how to retrieve them.
# These topics are covered in @sec-retrieving-open-data, which describes various geoportals, which collectively contain many terabytes of data, and how to use them.
# To further ease data access, a number of packages for downloading geographic data have been developed, as described in @sec-geographic-data-packages.
#
# There are many geographic file formats, each of which has pros and cons, described in @sec-file-formats.
# The process of reading and writing files efficiently is covered in Sections @sec-data-input and @sec-data-output, respectively.
#
# ## Retrieving open data {#sec-retrieving-open-data}
#
# A vast and ever-increasing amount of geographic data is available on the internet, much of which is free to access and use (with appropriate credit given to its providers).[^07-read-write-plot-1]
# In some ways there is now too much data, in the sense that there are often multiple places to access the same dataset.
# Some datasets are of poor quality.
# In this context, it is vital to know where to look, so the first section covers some of the most important sources.
# Various 'geoportals' (web services providing geospatial datasets such as [Data.gov](https://catalog.data.gov/dataset?metadata_type=geospatial)) are a good place to start, providing a wide range of data but often only for specific locations (as illustrated in the updated [Wikipedia page](https://en.wikipedia.org/wiki/Geoportal) on the topic).
#
# [^07-read-write-plot-1]: For example, visit <https://freegisdata.rtwilson.com/> for a vast list of websites with freely available geographic datasets.
#
# Some global geoportals overcome this issue.
# The [GEOSS portal](http://www.geoportal.org/) and the [Copernicus Open Access Hub](https://scihub.copernicus.eu/), for example, contain many raster datasets with global coverage.
# A wealth of vector datasets can be accessed from the [SEDAC](http://sedac.ciesin.columbia.edu/) portal run by the National Aeronautics and Space Administration (NASA) and the European Union's [INSPIRE geoportal](http://inspire-geoportal.ec.europa.eu/), with global and regional coverage.
#
# Most geoportals provide a graphical interface allowing datasets to be queried based on characteristics such as spatial and temporal extent, the United States Geological Survey's [EarthExplorer](https://earthexplorer.usgs.gov/) being a prime example.
# Exploring datasets interactively on a browser is an effective way of understanding available layers.
# From reproducibility and efficiency perspectives, downloading data is, however, best done with code.
# Downloads can be initiated from the command line using a variety of techniques, primarily via URLs and APIs (see the [Sentinel API](https://scihub.copernicus.eu/twiki/do/view/SciHubWebPortal/APIHubDescription), for example).
# Files hosted on static URLs can be downloaded with the following method, as illustrated in the code chunk below which accesses the [Natural Earth Data](https://www.naturalearthdata.com/) website to download the world airports layer zip file and to extract the contained ESRI Shapefile.
# Note that the download code is complicated by the fact that the server checks the `User-agent` header of the request, basically to make sure that the download takes place through a browser.
# To overcome this, we add a header corresponding to a request coming from a browser (such as Firefox) in our code.
# <!-- jn: the following code example looks fairly complex (I think it can be done with download.file only in R) -- cannot we simplify it somehow? -->

#| eval: false
# Set URL+filename
url = 'https://www.naturalearthdata.com/http//www.naturalearthdata.com/download/10m/cultural/ne_10m_airports.zip'
filename = 'output/ne_10m_airports.zip'
# Download
opener = urllib.request.build_opener()
opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/116.0')]
urllib.request.install_opener(opener)
urllib.request.urlretrieve(url, filename)
# Extract
f = zipfile.ZipFile(filename, 'r')
f.extractall('output')
f.close()

#| echo: false
filename = 'output/ne_10m_airports.zip'

# The ESRI Shapefile that has been created in the `output` directory can then be imported and plotted (@fig-ne-airports) as follows using **geopandas**.

#| label: fig-ne-airports
#| fig-cap: World airports layer, downloaded from the Natural Earth Data website using Python
ne = gpd.read_file(filename.replace('.zip', '.shp'))
ne.plot();

# ## Geographic data packages {#sec-geographic-data-packages}
#
# Many Python packages have been developed for accessing geographic data, two of which are presented in @tbl-data-packages and demonstrated below.
# These provide interfaces to one or more spatial libraries or geoportals and aim to make data access even quicker from the command line.
# <!-- jn: a table with data packages should have more examples of packages (at least ~5)... we do not need, however, to explain all of them... is that possible? -->
#
# | Package     | Description                                                                                       |
# |-------------|---------------------------------------------------------------------------------------------------|
# | **cartopy** | Download layers from [Natural Earth Data](https://www.naturalearthdata.com/downloads/)            |
# | **osmnx**   | Access to [OpenStreetMap](https://www.openstreetmap.org/) data and conversion to spatial networks |
#
# : Selected Python packages for geographic data retrieval {#tbl-data-packages}
#
# Each data package has its own syntax for accessing data.
# This diversity is demonstrated in the subsequent code chunks, which show how to get data using the packages from @tbl-data-packages.
#
# Administrative borders are often useful in spatial analysis.
# These can be accessed with the `cartopy.io.shapereader.natural_earth` function from the **cartopy** package.
# For example, the following code loads the `'admin_2_counties'` dataset of US counties into a `GeoDataFrame` (@fig-ne-counties).

#| label: fig-ne-counties
#| fig-cap: US counties, downloaded from the Natural Earth Data website using package **cartopy**
filename = cartopy.io.shapereader.natural_earth(
    resolution='10m',
    category='cultural',
    name='admin_2_counties'
)
counties = gpd.read_file(filename)
counties.plot();

# <!-- jn: maybe it would be worth explaning why the visualization spans the whole world, not just the continental US? (I not it is obvious to many people, but I assume -- not all) -->
#
# Other layers can be accessed the same way.
# You need to specify the `resolution`, `category`, and `name` of the requested dataset in [Natural Earth Data](https://www.naturalearthdata.com/downloads/), then  run the `cartopy.io.shapereader.natural_earth`, which downloads the file(s) and returns the path, and read the file into the Python environment, e.g., using `gpd.read_file`.
# This is an alternative approach to "directly" downloading files as shown earlier (@sec-retrieving-open-data).
#
# The second example uses the **osmnx** package to find parks from the OpenStreetMap (OSM) database.
# As illustrated in the code-chunk below, OpenStreetMap data can be obtained using the `ox.features.features_from_place` function.
# The first argument is a string which is geocoded to a polygon (the `ox.features.features_from_bbox` and `ox.features.features_from_polygon` can also be used to query a custom area of interest).
# The second argument specifies the OSM tag(s), selecting which OSM elements we're interested in (parks, in this case), represented by key-value pairs.
# <!-- jn: maybe this is a place to mention https://wiki.openstreetmap.org/wiki/Map_features ? -->

parks = ox.features.features_from_place(
    query='leeds uk', 
    tags={'leisure': 'park'}
)

# The result is a `GeoDataFrame` with the parks in Leeds.
# Now, we can plots the geometries with the `name` property in the tooltips using `explore` (@fig-ox-features).

#| label: fig-ox-features
#| fig-cap: Parks in Leeds, based on OpenStreetMap data, downloaded using package **osmnx**
parks[['name', 'geometry']].explore()

# It should be noted that the **osmnx** package downloads OSM data from the [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API), which is rate limited and therefore unsuitable for queries covering very large areas.
# To overcome this limitation, you can download OSM data extracts, such as in Shapefile format from [Geofabrik](https://download.geofabrik.de/), and then load them from the file into the Python environment.
# <!-- jn: it seems that on the Geofabrik website there is no Shapefile format available for download (except for Antarctica)... we need to fix the above sentence... -->
#
# OpenStreetMap is a vast global database of crowd-sourced data, is growing daily, and has a wider ecosystem of tools enabling easy access to the data, from the [Overpass turbo](https://overpass-turbo.eu/) web service for rapid development and testing of OSM queries to [osm2pgsql](https://osm2pgsql.org/) for importing the data into a PostGIS database.
# Although the quality of datasets derived from OSM varies, the data source and wider OSM ecosystems have many advantages: they provide datasets that are available globally, free of charge, and constantly improving thanks to an army of volunteers.
# Using OSM encourages 'citizen science' and contributions back to the digital commons (you can start editing data representing a part of the world you know well at [www.openstreetmap.org](https://www.openstreetmap.org/)).
#
# Sometimes, packages come with built-in datasets.
# These can be accessed just like any other object (e.g., function) that is imported as part of the package, or in other ways as specified in the package documentation.
# For example, package **geopandas** comes with few built-in datasets (see `gpd.datasets.available` for a list of names).
# Using the `gpd.datasets.get_path` function and the dataset name, we can obtain the path to the location of the dataset file on our computer.
# For example, `'naturalearth_lowres'` is a vector layer of world countries (from Natural Earth Data, which we have already seen before):

ne_filename = gpd.datasets.get_path('naturalearth_lowres')
ne_filename

# <!-- jn: the above code returns a warning -- please update the example -->
#
# Then, we can import the dataset, just like from any other file with `gpd.read_file`.

ne = gpd.read_file(ne_filename)

# Another way to obtain spatial information is to perform geocoding---transform a description of a location, usually an address, into a set of coordinates.
# This is typically done by sending a query to an online service and getting the location as a result.
# Many such services exist that differ in the used method of geocoding, usage limitations, costs, or API key requirements.
# [Nominatim](https://nominatim.openstreetmap.org/ui/about.html) is a popular free service, based on OpenStreetMap data.
# It can be accessed in Python uisng the `osmnx.geocoder.geocode` function.
# The function returns a `tuple` of the `(lat,lon)` form.
# <!-- jn: in what CRS? maybe it would be good to add this info -->
# The example below searches for John Snow blue plaque coordinates located on a building in the Soho district of London.
# <!-- jn: maybe we should add a website about the John Snow blue plaque? not everyone is probably familiar with it... -->

ox.geocoder.geocode('54 Frith St, London W1D 4SJ, UK')

# If the query returns no results, an `InsufficientResponseError` is raised, a scenario that the user can deal with using [`try`/`except`](https://docs.python.org/3/tutorial/errors.html#handling-exceptions).
# <!--jn: what do you mean by "deal" here? what is the expected outcome? how to deal with it? -->
#
# The alternative function `osmnx.geocoder.geocode_to_gdf` can be used to automatically geocode multiple addresses (accepting a `list` of `string`s) and transforming them into a `GeoDataFrame`.
# This function also returns `'Polygon'` geometries.
# <!-- jn: why "also"? -->
# <!-- jn: why Polygon geometries? what is the logic behind it? -->

result = ox.geocoder.geocode_to_gdf(['54 Frith St, London W1D 4SJ, UK'])
result

# The result is visualized in @fig-ox-geocode using the `.explore` function.

#| label: fig-ox-geocode
#| fig-cap: Specific address in London, geocoded into a `GeoDataFrame` using package **osmnx**
result[['display_name', 'geometry']].explore(color='red')

# ```{=html}
# <!-- ## Geographic web services
#
# To complete... -->
# ```
#
# ## File formats {#sec-file-formats}
#
# Geographic datasets are usually stored as files or in spatial databases.
# File formats usually can either store vector or raster data, while spatial databases such as [PostGIS](https://postgis.net/) can store both.
# The large variety of file formats may seem bewildering, but there has been much consolidation and standardization since the beginnings of GIS software in the 1960s when the first widely distributed program ([SYMAP](https://news.harvard.edu/gazette/story/2011/10/the-invention-of-gis/)) for spatial analysis was created at Harvard University [@coppock_history_1991].
#
# GDAL (which originally was pronounced as "goo-dal", with the double "o" making a reference to object-orientation), the Geospatial Data Abstraction Library, has resolved many issues associated with incompatibility between geographic file formats since its release in 2000.
# GDAL provides a unified and high-performance interface for reading and writing of many raster and vector data formats.
# Many open and proprietary GIS programs, including GRASS, ArcGIS and QGIS, use GDAL behind their GUIs for doing the legwork of ingesting and spitting out geographic data in appropriate formats.
# Most Pyhton packages for working with spatial data, including **geopandas** and **rasterio** used in this book, also rely on GDAL for importing and exporting spatial data files.
#
# GDAL provides access to more than 200 vector and raster data formats.
# @tbl-file-formats presents some basic information about selected and often used spatial file formats.
#
# | Name              | Extension              | Info                                                                                                                                                                                               | Type                             | Model          |
# |-------------------|------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------|----------------|
# | ESRI Shapefile    | `.shp` (the main file) | Popular format consisting of at least three files. No support for: files \> 2GB;mixed types; names \> 10 chars; cols \> 255.                                                                       | Vector                           | Partially open |
# | GeoJSON           | `.geojson`             | Extends the JSON exchange format by including a subset of the simple feature representation; mostly used for storing coordinates in longitude and latitude; it is extended by the TopoJSON format. | Vector                           | Open           |
# | KML               | `.kml`                 | XML-based format for spatial visualization, developed for use with Google Earth. Zipped KML file forms the KMZ format.                                                                             | Vector                           | Open           |
# | GPX               | `.gpx`                 | XML schema created for exchange of GPS data.                                                                                                                                                       | Vector                           | Open           |
# | FlatGeobuf        | `.fgb`                 | Single file format allowing for quick reading and writing of vector data. Has streaming capabilities.                                                                                              | Vector                           | Open           |
# | GeoTIFF           | `.tif/.tiff`           | Popular raster format. A TIFF file containing additional spatial metadata.                                                                                                                         | Raster                           | Open           |
# | Arc ASCII         | `.asc`                 | Text format where the first six lines represent the raster header, followed by the raster cell values arranged in rows and columns.                                                                | Raster                           | Open           |
# | SQLite/SpatiaLite | `.sqlite`              | Standalone relational database, SpatiaLite is the spatial extension of SQLite.                                                                                                                     | Vector and raster                | Open           |
# | ESRI FileGDB      | `.gdb`                 | Spatial and nonspatial objects created by ArcGIS. Allows: multiple feature classes; topology. Limited support from GDAL.                                                                           | Vector and raster                | Proprietary    |
# | GeoPackage        | `.gpkg`                | Lightweight database container based on SQLite allowing an easy and platform-independent exchange of geodata                                                                                       | Vector and (very limited) raster | Open           |
#
# : Commonly used spatial data file formats {#tbl-file-formats}
#
# An important development ensuring the standardization and open-sourcing of file formats was the founding of the Open Geospatial Consortium ([OGC](http://www.opengeospatial.org/)) in 1994.
# Beyond defining the simple features data model (see @sec-simple-features), the OGC also coordinates the development of open standards, for example as used in file formats such as KML and GeoPackage.
# <!-- jn: simple features or Simple Features? -->
# Open file formats of the kind endorsed by the OGC have several advantages over proprietary formats: the standards are published, ensure transparency and open up the possibility for users to further develop and adjust the file formats to their specific needs.
#
# ESRI Shapefile is the most popular vector data exchange format; however, it is not an fully open format (though its specification is open).
# It was developed in the early 1990s and, from a modern standpoint, has a number of limitations.
# First of all, it is a multi-file format, which consists of at least three files.
# It also only supports 255 columns, its column names are restricted to ten characters and the file size limit is 2 GB.
# Furthermore, ESRI Shapefile does not support all possible geometry types, for example, it is unable to distinguish between a polygon and a multipolygon.
# Despite these limitations, a viable alternative had been missing for a long time.
# In 2014, [GeoPackage](https://www.geopackage.org/) emerged, and seems to be a more than suitable replacement candidate for ESRI Shapefile.
# GeoPackage is a format for exchanging geospatial information and an OGC standard.
# This standard describes the rules on how to store geospatial information in a tiny SQLite container.
# Hence, GeoPackage is a lightweight spatial database container, which allows the storage of vector and raster data but also of non-spatial data and extensions.
# Aside from GeoPackage, there are other geospatial data exchange formats worth checking out (@tbl-file-formats).
#
# The GeoTIFF format seems to be the most prominent raster data format.
# It allows spatial information, such as the CRS definition and the transformation matrix (see @sec-using-rasterio), to be embedded within a TIFF file.
# Similar to ESRI Shapefile, this format was firstly developed in the 1990s, but as an open format.
# Additionally, GeoTIFF is still being expanded and improved.
# One of the most significant recent addition to the GeoTIFF format is its variant called COG (Cloud Optimized GeoTIFF).
# Raster objects saved as COGs can be hosted on HTTP servers, so other people can read only parts of the file without downloading the whole file (@sec-input-raster).
#
# There is also a plethora of other spatial data formats that we do not explain in detail or mention in @tbl-file-formats due to the book limits.
# If you need to use other formats, we encourage you to read the GDAL documentation about [vector](https://gdal.org/drivers/vector/index.html) and [raster](https://gdal.org/drivers/raster/index.html) drivers.
# Additionally, some spatial data formats can store other data models (types) than vector or raster.
# It includes LAS and LAZ formats for storing lidar point clouds, and NetCDF and HDF for storing multidimensional arrays.
#
# Finally, spatial data is also often stored using tabular (non-spatial) text formats, including CSV files or Excel spreadsheets.
# This can be convenient to share spatial (point) datasets with people who, or software that, struggle with spatial data formats.
# If necessary, the table can be converted to a point layer (see examples in @sec-vector-layer-from-scratch and @sec-spatial-joining).
#
# ## Data input (I) {#sec-data-input}
#
# Executing commands such as `geopandas.read_file` (the main function we use for loading vector data) or `rasterio.open`+`.read` (the main group of functions used for loading raster data) silently sets off a chain of events that reads data from files.
# Moreover, there are many Python packages containing a wide range of geographic data or providing simple access to different data sources.
# All of them load the data into the Python environment or, more precisely, assign objects to your workspace, stored in RAM and accessible within the Python session.
# <!-- jn: what with large (>RAM) rasters? -->
#
# ### Vector data
#
# Spatial vector data comes in a wide variety of file formats.
# Most popular representations such as `.shp`, `.geojson`, and `.gpkg` files can be imported and exported with **geopandas** functions `read_file` and `to_file` (covered in @sec-data-output), respectively.
#
# **geopandas** uses GDAL to read and write data, via **fiona** (the [default](https://github.com/geopandas/geopandas/issues/2217)) or **pyogrio** packages (a recently developed alternative to **fiona**).
# <!-- jn: as far as I understand, pyogrio will be the default in the future, right? if so, we should mention it here -->
# <!-- jn: also, given the above, which one should be present? -->
# After **fiona** is imported, the command `fiona.supported_drivers` can be used to list drivers available to GDAL, including whether they can (`'r'`), append (`'a'`), or write (`'w'`) data, or all three.

#| eval: false
fiona.supported_drivers

# ```
# {'DXF': 'rw',
#  'CSV': 'raw',
#  ...   
#  'TopoJSON': 'r',
#  'LIBKML': 'r'}
# ```
#
# Other, less common, drivers can be ["activated"](https://geopandas.org/en/stable/docs/user_guide/io.html) by manually supplementing `fiona.supported_drivers`.
#
# The first argument of the **geopandas** versatile data import function `gpd.read_file` is `filename`, which is typically a string, but can also be a file connection.
# The content of a string could vary between different drivers.
# In most cases, as with the ESRI Shapefile (`.shp`) or the GeoPackage format (`.gpkg`), the `filename` argument would be a path or a URL to an actual file, such as `geodata.gpkg`.
# The driver is automatically selected based on the file extension, as demonstrated for a `.gpkg` file below.

world = gpd.read_file('data/world.gpkg')

# For some drivers, such as a File Geodatabase (`OpenFileGDB`), `filename` could be provided as a folder name.
# GeoJSON, a plain text format, on the other hand, can be read from a `.geojson` file, but also from a string.

gpd.read_file('{"type":"Point","coordinates":[34.838848,31.296301]}')

# Some vector formats, such as GeoPackage, can store multiple data layers.
# By default, `gpd.read_file` reads the first layer of the file specified in `filename`.
# However, using the `layer` argument you can specify any other layer.
#
# The `gpd.read_file` function also allows for reading just parts of the file into RAM with two possible mechanisms.
# The first one is related to the `where` argument, which allows specifying what part of the data to read using an SQL `WHERE` expression.
# An example below extracts data for Tanzania only from the `world.gpkg` file (@fig-read-shp-query (a)).
# It is done by specifying that we want to get all rows for which `name_long` equals to `'Tanzania'`.

tanzania = gpd.read_file('data/world.gpkg', where='name_long="Tanzania"')
tanzania

# If you do not know the names of the available columns, a good approach is to just read one row of the data using the `rows` argument, which can be used to read the first N rows, then use the `.columns` property to examine the column names:

gpd.read_file('data/world.gpkg', rows=1).columns

# The second mechanism uses the `mask` argument to filter data based on intersection with an existing geometry.
# This argument expects a geometry (`GeoDataFrame`, `GeoSeries`, or `shapely` geometry) representing the area where we want to extract the data.
# Let's try it using a small example---we want to read polygons from our file that intersect with the buffer of 50,000 $m$ of Tanzania's borders.
# To do it, we need to transform the geometry to a projected CRS (such as `EPSG:32736`), prepare our "filter" by creating the buffer (@sec-buffers), and    transform back to the original CRS to be used as a mask (@fig-read-shp-query (a)).

tanzania_buf = tanzania.to_crs(32736).buffer(50000).to_crs(4326)

# Now, we can pass the "filter" geometry `tanzania_buf` to the `mask` argument of `gpd.read_file`.

tanzania_neigh = gpd.read_file('data/world.gpkg', mask=tanzania_buf)

# Our result, shown in @fig-read-shp-query (b), contains Tanzania and every country intersecting with its 50,000 $m$ buffer.
# Note that the last two expressions are used to add text labels with the `name_long` of each country, placed at the country centroid.

#| label: fig-read-shp-query
#| fig-cap: Reading a subset of the vector layer file `world.gpkg`
#| layout-ncol: 2
#| fig-subcap: 
#| - Using a `where` query (matching `'Tanzania'`)
#| - Using a `mask` (a geometry shown in red)
# Using 'where'
fig, ax = plt.subplots()
tanzania.plot(ax=ax, color='lightgrey', edgecolor='grey')
tanzania.apply(lambda x: ax.annotate(text=x['name_long'], 
               xy=x.geometry.centroid.coords[0], ha='center'), axis=1);
# Using 'mask'
fig, ax = plt.subplots()
tanzania_neigh.plot(ax=ax, color='lightgrey', edgecolor='grey')
tanzania_buf.plot(ax=ax, color='none', edgecolor='red')
tanzania_neigh.apply(lambda x: ax.annotate(text=x['name_long'],
                     xy=x.geometry.centroid.coords[0], ha='center'), axis=1);

# A different, `gpd.read_postgis`, function can be used to read a vector layer from a PostGIS database.
#
# Often we need to read CSV files (or other tabular formats) which have x and y coordinate columns, and turn them into a `GeoDataFrame` with point geometries.
# To do that, we can import the file using **pandas** (e.g., using `pd.read_csv` or `pd.read_excel`), then go from `DataFrame` to `GeoDataFrame` using the `gpd.points_from_xy` function, as shown earlier in the book (See @sec-vector-layer-from-scratch and @sec-spatial-joining).
# For example, the table `cycle_hire_xy.csv`, where the coordinates are stored in the `X` and `Y` columns in `EPSG:4326`, can be imported, converted to a `GeoDataFrame`, and plotted, as follows (@fig-cycle_hire_xy-layer).

#| label: fig-cycle_hire_xy-layer
#| fig-cap: The `cycle_hire_xy.csv` table transformed to a point layer
cycle_hire = pd.read_csv('data/cycle_hire_xy.csv')
geom = gpd.points_from_xy(cycle_hire['X'], cycle_hire['Y'], crs=4326)
geom = gpd.GeoSeries(geom)
cycle_hire_xy = gpd.GeoDataFrame(data=cycle_hire, geometry=geom)
cycle_hire_xy.plot();

# Instead of columns describing 'XY' coordinates, a single column can also contain the geometry information, not necessarily points but possible any other geometry type.
# Well-known text (WKT), well-known binary (WKB), and GeoJSON are examples of formats used to encode geometry in such a column.
# For instance, the `world_wkt.csv` file has a column named `'WKT'`, representing polygons of the world's countries (in WKT format).
# To import and convert it to a `GeoDataFrame`, we can apply the `shapely.from_wkt` function (@sec-geometries) on the WKT strings, to convert them into `shapely` geometries (@fig-world_wkt-layer).
# <!-- jn: maybe it would be good to explain the `.apply` function here (or somewhere) -->

#| label: fig-world_wkt-layer
#| fig-cap: The `world_wkt.csv` table transformed to a polygon layer
world_wkt = pd.read_csv('data/world_wkt.csv')
world_wkt['geometry'] = world_wkt['WKT'].apply(shapely.from_wkt)
world_wkt = gpd.GeoDataFrame(world_wkt)
world_wkt.plot();

# ::: callout-note
# Not all of the supported vector file formats store information about their coordinate reference system.
# <!-- jn: what are the examples of such formats? -->
# In these situations, it is possible to add the missing information using the `.set_crs` function.
# Please refer also to @sec-querying-and-setting-coordinate-systems for more information.
# :::
#
# As a final example, we will show how **geopandas** also reads KML files.
# A KML file stores geographic information in XML format---a data format for the creation of web pages and the transfer of data in an application-independent way [@nolan_xml_2014].
# Here, we access a KML file from the web.
# First, if necessary, we may need to "activate" the `KML` driver, which is not always available by default (just one of these expressions should be sufficient, depending on your system).

fiona.supported_drivers['KML'] = 'r'
fiona.supported_drivers['LIBKML'] = 'r'

# The sample KML file `KML_Samples.kml` contains more than one layer.
# To list the available layers, we can use the `fiona.listlayers` function.
# <!-- jn: maybe we could introduce this function earlier, for example around this sentence: "However, using the `layer` argument you can specify any other layer." -->

u = 'https://developers.google.com/kml/documentation/KML_Samples.kml'
fiona.listlayers(u)

# We can choose, for instance, the first layer `'Placemarks'` and read it, using `gpd.read_file` with an additional `layer` argument.

placemarks = gpd.read_file(u, layer='Placemarks')
placemarks

# ### Raster data {#sec-input-raster}
#
# Similar to vector data, raster data comes in many file formats, some of which support multilayer files.
# `rasterio.open` is used to create a file connection to a raster file, which can be subsequently used to read the metadata and/or the values, as shown previously (@sec-using-rasterio).

src = rasterio.open('data/srtm.tif')
src

# All of the previous examples, like the one above, read spatial information from files stored on your hard drive.
# However, GDAL also allows reading data directly from online resources, such as HTTP/HTTPS/FTP web resources.
# The only thing we need to do is to add a `/vsicurl/` or `/vsicurl_streaming/` (see [here](https://gis.stackexchange.com/questions/450105/using-rasterio-to-read-ndvi-data-from-gimmss-cog-products)) prefix before the path to the file.
# Let's try it by connecting to the global monthly snow probability at 500 $m$ resolution for the period 2000-2012 [@hengl_t_2021_5774954].
# Snow probability for December is stored as a Cloud Optimized GeoTIFF (COG) file (see @sec-file-formats).
# To read an online file, we need to provide its URL together with the `/vsicurl_streaming/` prefix.

#| eval: false
src = rasterio.open('/vsicurl_streaming/https://zenodo.org/record/5774954/files/clm_snow.prob_esacci.dec_p.90_500m_s0..0cm_2000..2012_v2.0.tif')
src

# In the example above `rasterio.open` creates a connection to the file without obtaining any values, as we did for the local `srtm.tif` file.
# The values can be read into an `ndarray` using the `.read` method of the file connection (@sec-using-rasterio).
# Using parameters of `.read` allows us to just read a small portion of the data, without downloading the entire file.
# This is very useful when working with large datasets hosted online from resource-constrained computing environments such as laptops.
#
# For example, we can read a specified rectangular extent of the raster.
# With **rasterio**, this is done using the so-called [windowed reading](https://rasterio.readthedocs.io/en/latest/topics/windowed-rw.html) capabilities.
# Note that, with windowed reading, we import just a subset of the raster extent into an `ndarray` covering any partial extent.
# Windowed reading is therefore memory- (and, in this case, bandwidth-) efficient, since it avoids reading the entire raster into memory.
# It can also be considered an alternative pathway to *cropping* (@sec-raster-cropping).
#
# To read a raster *window*, let's first define the bounding box coordinates.
# For example, here we use a $10 \times 10$ degrees extent coinciding with Reykjavik.

#| eval: false
xmin=-30
xmax=-20
ymin=60
ymax=70

# Using the extent coordinates along with the raster transformation matrix, we create a window object, using the [`rasterio.windows.from_bounds`](https://rasterio.readthedocs.io/en/stable/api/rasterio.windows.html#rasterio.windows.from_bounds) function.
# This function basically "translates" the extent from coordinates, to row/column ranges.

#| eval: false
w = rasterio.windows.from_bounds(
    left=xmin, 
    bottom=ymin,
    right=xmax,
    top=ymax, 
    transform=src.transform
)
w

# <!-- jn: why eval:false for these examples? the output is not shown... -->
#
# Now we can read the partial array, according to the specified window `w`, by passing it to the `.read` method.

#| eval: false
r = src.read(1, window=w)
r

# Note that the transformation matrix of the window is not the same as that of the original raster (unless it incidentally starts from the top-left corner)!
# Therefore, we must re-create the transformation matrix, with the modified origin (`xmin`,`ymax`), yet the same resolution, as follows.

#| eval: false
w_transform = rasterio.transform.from_origin(
    west=xmin, 
    north=ymax, 
    xsize=src.transform[0],
    ysize=abs(src.transform[4])
)
w_transform

# The array `r` along with the updated transformation matrix `w_transform` comprise the partial window, which we can keep working with just like with any other raster, as shown in previous chapters.
# @fig-raster-window shows the result, along with the location of Reykjavik.

#| label: fig-raster-window
#| fig-cap: Raster window read from a remote Cloud Optimized GeoTIFF (COG) file source
#| eval: false
fig, ax = plt.subplots()
rasterio.plot.show(r, transform=w_transform, ax=ax)
gpd.GeoSeries(shapely.Point(-21.94, 64.15)).plot(ax=ax, color='red');

# Another option is to extract raster values at particular points, directly from the file connection, using the `.sample` method (see @sec-spatial-subsetting-raster).
# For example, we can get the snow probability for December in Reykjavik (70%) by specifying its coordinates and applying `.sample`.

#| eval: false
coords = (-21.94, 64.15)
values = src.sample([coords])
list(values)

# The example above efficiently extracts and downloads a single value instead of the entire GeoTIFF file, saving valuable resources.
#
# The `/vsicurl/` prefix also works for *vector* file formats, enabling you to import datasets from online storage with **geopandas** just by adding it before the vector file URL.
# Importantly, `/vsicurl/` is not the only prefix provided by GDAL---many more exist, such as `/vsizip/` to read spatial files from ZIP archives without decompressing them beforehand or `/vsis3/` for on-the-fly reading files available in AWS S3 buckets.
# You can learn more about it at <https://gdal.org/user/virtual_file_systems.html>.
#
# ## Data output (O) {#sec-data-output}
#
# Writing geographic data allows you to convert from one format to another and to save newly created objects for permanent storage.
# Depending on the data type (vector or raster), object class (e.g., `GeoDataFrame`), and type and amount of stored information (e.g., object size, range of values), it is important to know how to store spatial files in the most efficient way.
# The next two subsections will demonstrate how to do this.
#
# ### Vector data
#
# The counterpart of `gpd.read_file` is the `.to_file` method that a `GeoDataFrame` has.
# It allows you to write `GeoDataFrame` objects to a wide range of geographic vector file formats, including the most common ones, such as `.geojson`, `.shp` and `.gpkg`.
# Based on the file name, `.to_file` decides automatically which driver to use.
# The speed of the writing process depends also on the driver.
#
# For example, to export the `world` layer to a GeoPackage file, we can use `.to_file` and specify the output file name.

world.to_file('output/world.gpkg')

# Note, that if you try to write to the same data source again, the function will overwrite the file.

world.to_file('output/world.gpkg')

# Instead of overwriting the file, we could add a new layer to the file with `mode='a'` ("append" mode, as opposed to the default `mode='w'` for the "write" mode).
# <!-- jn: "a new layer"? or add new rows? -->
# Appending is supported by several spatial formats, including GeoPackage.

world.to_file('output/world_many_features.gpkg')
world.to_file('output/world_many_features.gpkg', mode='a')

# Now, `world_many_features.gpkg` contains a polygonal layer named `world` with two "copies" of each country (that is 177×2=354 features, whereas the `world` layer has 177 features).

gpd.read_file('output/world_many_features.gpkg').shape

# Alternatively, you can create another, separate, layer, within the same file, which is supported by some formats, including GeoPackage.

world.to_file('output/world_many_layers.gpkg')
world.to_file('output/world_many_layers.gpkg', layer='world2')

# In this case, `world_many_layers.gpkg` has two "layers": `world_many_layers` (same as the file name, when `layer` is unspecified) and `world2`.
# Incidentally, the contents of the two layers is identical, but this does not have to be.
# Each layer from such a file can be imported separately using the `layer` argument of `gpd.read_file`.

#| eval: false
layer1 = gpd.read_file('output/world_many_layers.gpkg', layer='world_many_layers')
layer2 = gpd.read_file('output/world_many_layers.gpkg', layer='world2')

# ### Raster data {#sec-data-output-raster}
#
# To write a raster file using **rasterio**, we need to pass a raster file path to `rasterio.open` in writing (`'w'`) mode.
# This implies creating a new empty file (or overwriting an existing one).
# Next, we need to write the raster values to the file using the `.write` method of the file connection.
# Finally, we should close the file connection using the `.close` method.
#
# As opposed to reading mode (`'r'`, the default) mode, the `rasterio.open` function in writing mode needs quite a lot of information, in addition to the file path and mode:
#
# -   `driver`---The file format. The general recommendation is `'GTiff'` for GeoTIFF, but other formats are also supported (see @tbl-file-formats)
# -   `height`---Number of rows
# -   `width`---Number of columns
# -   `count`---Number of bands
# -   `nodata`---The value which represents "No Data", if any
# -   `dtype`---The raster data type, one of **numpy** types (e.g., `np.int64`) (see @tbl-numpy-data-types)
# -   `crs`---The CRS, e.g., using an EPSG code (such as `4326`)
# -   `transform`---The transform matrix
# -   `compress`---A compression method to apply, such as `'lzw'`. This is optional and most useful for large rasters. Note that, at the time of writing, this [does not work well](https://gis.stackexchange.com/questions/404738/why-does-rasterio-compression-reduces-image-size-with-single-band-but-not-with-m) for writing multiband rasters
#
# Once the file connection with the right metadata is ready, we do the actual writing using the `.write` method of the file connection.
# If there are several bands we may execute the `.write` method several times, as in `.write(a,n)`, where `a` is the array with band values and `n` is the band index (starting from `1`, see below).
# When done, we close the file connection using the `.close` method.
# Some functions, such as `rasterio.warp.reproject` used for resampling and reprojecting (@sec-raster-resampling and @sec-reprojecting-raster-geometries) directly accept a file connection in `'w'` mode, thus handling the writing (of a resampled or reprojected raster) for us.
#
# Most of the properties are either straightforward to choose, based on our aims, (e.g., `driver`, `crs`, `compress`, `nodata`), or directly derived from the array with the raster values itself (e.g., `height`, `width`, `count`, `dtype`).
# The most complicated property is the `transform`, which specifies the raster origin and resolution.
# The `transform` is typically either obtained from an existing raster (serving as a "template"), created from scratch based on manually specified origin and resolution values (e.g., using `rasterio.transform.from_origin`), or calculated automatically (e.g., using `rasterio.warp.calculate_default_transform`), as shown in previous chapters.
#
# Earlier in the book, we have already demonstrated the four most common scenarios of writing rasters, covering the above-mentioned considerations:
# <!-- jn: there are five scenarios, not four, right? (see below) -->
#
# -   Creating from scratch (@sec-raster-from-scratch)---we created and wrote two rasters from scratch by associating the `elev` and `grain` arrays with an arbitrary spatial extent. The custom arbitrary transformation matrix was created using `rasterio.transform.from_origin`
# -   Aggregating (@sec-raster-agg-disagg)---we wrote an aggregated a raster, by resampling from an exising raster file, then updating the transformation matrix using `.transform.scale`
# -   Resampling (@sec-raster-resampling)---we resampled a raster into a custom grid, manually creating the transformation matrix using `rasterio.transform.from_origin`, then resampling and writing the output using `rasterio.warp.reproject`
# -   Masking and cropping (@sec-raster-cropping)---we wrote masked and/or cropped arrays from a raster, possibly updating the transformation matrix and dimensions (when cropping)
# -   Reprojecting (@sec-reprojecting-raster-geometries)---we reprojected a raster into another CRS, by automatically calculating an optimal `transform` using `rasterio.warp.calculate_default_transform`, then resampling and writing the output using `rasterio.warp.reproject`
#
# To summarize, the raster-writing scenarios differ in two aspects:
#
# 1.  The way that the transformation matrix for the output raster is obtained:
#     -   Imported from an existing raster (see below)
#     -   Created from scratch, using `rasterio.transform.from_origin` (@sec-raster-from-scratch)
#     -   Calculate automatically, using `rasterio.warp.calculate_default_transform` (@sec-reprojecting-raster-geometries)
# 2.  The way that the raster is written:
#     -   Using the `.write` method, given an existing array (@sec-raster-from-scratch, @sec-raster-agg-disagg)
#     -   Using `rasterio.warp.reproject` to calculate and write a resampled or reprojected array (@sec-raster-resampling, @sec-reprojecting-raster-geometries)
#
# A miminal example of writing a raster file named `r.tif` from scratch, to remind the main concepts, is given below.
# First, we create a small $2 \times 2$ array.

r = np.array([1,2,3,4]).reshape(2,2).astype(np.int8)
r

# Next, we define a transformation matrix, specifying the origin and resolution.

new_transform = rasterio.transform.from_origin(
    west=-0.5, 
    north=51.5, 
    xsize=2, 
    ysize=2
)
new_transform

# Then, we establish the writing-mode file connection to `r.tif`, which will be eithe created or overwritten.

dst = rasterio.open(
    'output/r.tif', 'w', 
    driver = 'GTiff',
    height = r.shape[0],
    width = r.shape[1],
    count = 1,
    dtype = r.dtype,
    crs = 4326,
    transform = new_transform
)
dst

# Next, we write the array of values into the file connection with the `.write` method.

dst.write(r, 1)

# Finally, we close the connection.

dst.close()

# These expressions, taken together, create a new file `output/r.tif`, which is a $2 \times 2$ raster, having a 2 decimal degree resolution, with the top-left corner placed over London.
#
# To make the picture of raster export complete, there are three important concepts we have not covered yet: array and raster data types, writing multiband rasters, and handling "No Data" values.
#
# Arrays (i.e., `ndarray` objects defined in package **numpy**) are used to store raster values when reading them from file, using `.read` (@sec-using-rasterio).
# All values in an array are of the same type, whereas the **numpy** package supports numerous numeric data types of various precision (and, accordingly, memory footprint).
# Raster formats, such as GeoTIFF, support exactly the same data types as **numpy**, which means that reading a raster file uses as little RAM as possible.
# The most useful types for raster data are summarized in @tbl-numpy-data-types.
#
# | Data type | Description                                           |
# |-----------|-------------------------------------------------------|
# | `int8`    | Integer in a single byte (`-128` to `127`)            |
# | `int16`   | Integer in 16 bits (`-32768` to `32767`)              |
# | `int32`   | Integer in 32 bits (`-2147483648` to `2147483647`)    |
# | `int64`   | Integer in 64 bits (`-9223372036854775808` to `9223372036854775807`) |
# | `uint8`   | Unsigned integer in 8 bits (`0` to `255`) |
# | `uint16`  | Unsigned integer in 16 bits (`0` to `65535`) |
# | `uint32`  | Unsigned integer in 32 bits (`0` to `4294967295`) |
# | `uint64` | Unsigned integer in 64 bits (`0` to `18446744073709551615`) |
# | `float16` | Half-precision (16 bit) float (`-65504` to `65504`)   |
# | `float32` | Single-precision (32 bit) float (`1e-38` to `1e38`)   |
# | `float64` | Double-precision (64 bit) float (`1e-308` to `1e308`) |
#
# : Commonly used **numpy** data types for rasters {#tbl-numpy-data-types}
#
# The raster data type needs to be specified when writing a raster, typically using the same type as that of the array to be written (see last example).
# For an existing raster file, the data type can be access through the `.dtype` property of the metadata (`.meta['dtype']`).

rasterio.open('output/r.tif').meta['dtype']

# The file `r.tif` has the data type `np.int8`, which we specified when creating it according to the data type of the original array.

r.dtype

# When reading the data back into the Python session, the array with the same data type is recreated.

rasterio.open('output/r.tif').read().dtype

# <!-- jn: I do not fully understand the story told by the last three code chunks... -->
# <!-- e.g., "which we specified when creating it according to the data type of the original array" when? maybe explain the difference between the first and third code chunk? -->
#
# Writing multiband rasters is similar to writing single-band rasters, only that we need to:
#
# -   Define a number of bands other than `count=1`, according to the number of bands we are going to write
# -   Execute the `.write` method multiple times, once for each layer
#
# For completeness, let's demonstrate writing a multi-band raster named `r3.tif`, which is similar to `r.tif`, but having three bands with values `r*1`, `r*2`, and `r*3` (i.e., the array `r` multiplied by `1`, `2`, or `3`).
# Since most of the metadata is going to be the same, this is also a good opportunity to (re-)demonstrate updating an existing metadata object rather than creating one from scratch.
# First, let's make a copy of the metadata we already have in `r.tif`.

dst_kwds = rasterio.open('output/r.tif').meta.copy()
dst_kwds

# Second, we update the `count` entry, replacing `1` (single-band) with `3` (three-band) using the `.update` method.

dst_kwds.update(count=3)
dst_kwds

# Finally, we can create a file connection using the updated metadata, write the values of the three bands, and close the connection.

dst = rasterio.open('output/r3.tif', 'w', **dst_kwds)
dst.write(r*1, 1)
dst.write(r*2, 2)
dst.write(r*3, 3)
dst.close()

# As a result, a three-band raster named `r3.tif` is created.
#
# Rasters often contain "No Data" values, representing missing data, for example, unreliable measurements due to clouds or pixels outside of the photographed extent.
# In a **numpy** `ndarray` object, "No Data" values may be represented by the special `np.nan` value.
# However, due to computer memory limitations, only arrays of type `float` can contain `np.nan`, while arrays of type `int` cannot.
# For `int` rasters containing "No Data", we typically mark missing data with a specific value beyond the valid range (e.g., `-9999`).
# The missing data "flag" definition is stored in the file (set through the `nodata` property of the file connection, see above).
# When reading an `int` raster with "No Data" back into Python, we need to be aware of the flag, if any.
# Let's demonstrate it through examples.
#
# We will start with the simpler case, rasters of type `float`.
# Since `float` arrays may contain the "native" value `np.nan`, representing "No Data" is straightforward.
# For example, suppose that we have a `float` array of size $2 \times 2$ containing one `np.nan` value.

r = np.array([1.1,2.1,np.nan,4.1]).reshape(2,2)
r

r.dtype

# When writing this type of array to a raster file, we do not need to specify any particular `nodata` "flag" value.

dst = rasterio.open(
    'output/r_nodata_float.tif', 'w', 
    driver = 'GTiff',
    height = r.shape[0],
    width = r.shape[1],
    count = 1,
    dtype = r.dtype,
    crs = 4326,
    transform = new_transform
)
dst.write(r, 1)
dst.close()

# This is equivalent to `nodata=None` (not shown).

#| eval: false
rasterio.open('output/r_nodata_float.tif').meta

# Reading from the raster back into the Python session reproduces the same exact array, including `np.nan`.

rasterio.open('output/r_nodata_float.tif').read()

# Now, conversely, suppose that we have an `int` array with missing data, where the "missing" value must inevitably be marked using a specific `int` "flag" value, such as `-9999` (remember that we can't store `np.nan` in an `int` array!).

r = np.array([1,2,-9999,4]).reshape(2,2).astype(np.int32)
r

r.dtype

# When writing the array to file, we must specify `nodata=-9999` to keep track of our "No Data" flag.

dst = rasterio.open(
    'output/r_nodata_int.tif', 'w', 
    driver = 'GTiff',
    height = r.shape[0],
    width = r.shape[1],
    count = 1,
    dtype = r.dtype,
    nodata = -9999,
    crs = 4326,
    transform = new_transform
)
dst.write(r, 1)
dst.close()

# Examining the metadata of the file we've just created confirms that the `nodata=-9999` setting was stored in the file `r_nodata_int.tif`.

rasterio.open('output/r_nodata_int.tif').meta

# If you try to open the file in GIS software, such as QGIS, you will see the missing data interpreted (e.g., the pixel shown as blank), meaning that the software is aware of the flag.
# However, reading the data back into Python reproduces an `int` array with `-9999`, due to the limitation of `int` arrays stated before/

src = rasterio.open('output/r_nodata_int.tif')
r = src.read()
r

# The Python user must therefore be mindful of "No Data" `int` rasters, for example to avoid interpreting the value `-9999` literally.
# For instance, if we "forget" about the `nodata` flag, the literal calculation of the `.mean` would incorrectly include the value `-9999`.

r.mean()

# There are two basic ways to deal with the situation: either converting the raster to `float` or using "No Data" mask.
# First, particularly with small rasters where memory constraints are irrelevant, it may be more convenient to go from `int` to `float`, to gain the ability of the natural `np.nan` representation.
# Here is how we can do this with `r_nodata_int.tif`.
# We detect the missing data flag, convert the raster to `float`, then assign `np.nan` into the cells that are supposed to be missing.

mask = r == src.nodata
r = r.astype(np.float64)
r[mask] = np.nan
r

# From there on, we deal with `np.nan` the usual way, such as using `np.nanmean` to calculate the mean excluding "No Data".

np.nanmean(r)

# The second approach is to read the values into a so-called ["masked" array](https://numpy.org/doc/stable/reference/maskedarray.generic.html#what-is-a-masked-array), using the argument `masked=True` of the `.read` method.
# A masked array can be thought of as an extended `ndarray`, with two components: `.data` (the values) and `.mask` (a corresponding boolean array marking "No Data" values).

r = src.read(masked=True)
r

# Complete treatment of masked arrays is beyond the scope of this book.
# However, the basic idea is that many **numpy** operations "honor" the mask, so that the user does not have to keep track of the way that "No Data" values are marked, similarly to the natural `np.nan` representation and regardless of the data type.
# For example, the `.mean` of a masked array ignores the value `-9999`, because it is masked, taking into account just the valid values `1`, `2`, and `4`.

r.mean()

# <!-- jn: maybe it would be good to compare pros and cons of these two approaches -->
#
# Finally, keep in mind that, confusingly, `float` rasters may represent "No Data" using a specific "flag" (such as `-9999.0`), instead, or in addition to (!), the native `np.nan` representation.
# In such cases, the same considerations shown for `int` apply to `float` rasters as well.
#
# ## Exercises
#
# ## References
