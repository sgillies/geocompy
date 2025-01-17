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

# # Raster-vector interactions {#sec-raster-vector}
#
# ## Prerequisites {.unnumbered}

#| echo: false
import pandas as pd
import matplotlib.pyplot as plt
pd.options.display.max_rows = 6
pd.options.display.max_columns = 6
pd.options.display.max_colwidth = 35
plt.rcParams['figure.figsize'] = (5, 5)

# This chapter requires importing the following packages:
# <!--jn:two packages are commented out -- should these lines be removed?-->
# <!--md: yes, done-->

import numpy as np
import shapely
import matplotlib.pyplot as plt
import geopandas as gpd
import rasterio
import rasterio.mask
import rasterstats
import rasterio.plot
import rasterio.features
import math
import os

# It also relies on the following data files:

src_srtm = rasterio.open('data/srtm.tif')
src_nlcd = rasterio.open('data/nlcd.tif')
src_grain = rasterio.open('output/grain.tif')
src_elev = rasterio.open('output/elev.tif')
src_dem = rasterio.open('data/dem.tif')
zion = gpd.read_file('data/zion.gpkg')
zion_points = gpd.read_file('data/zion_points.gpkg')
cycle_hire_osm = gpd.read_file('data/cycle_hire_osm.gpkg')
us_states = gpd.read_file('data/us_states.gpkg')
nz = gpd.read_file('data/nz.gpkg')
src_nz_elev = rasterio.open('data/nz_elev.tif')

# ## Introduction
#
# This chapter focuses on interactions between raster and vector geographic data models, both introduced in @sec-spatial-class.
# It includes four main techniques:
#
# -   Raster cropping and masking using vector objects (@sec-raster-cropping)
# -   Extracting raster values using different types of vector data (Section @sec-raster-extraction)
# -   Raster-vector conversion (@sec-rasterization and @sec-spatial-vectorization)
#
# These concepts are demonstrated using data from in previous chapters, to understand their potential real-world applications.
#
# ## Raster masking and cropping {#sec-raster-cropping}
#
# Many geographic data projects involve integrating data from many different sources, such as remote sensing images (rasters) and administrative boundaries (vectors).
# Often the extent of input raster datasets is larger than the area of interest.
# In this case raster *masking*, *cropping*, or both, are useful for unifying the spatial extent of input data (@fig-raster-crop (b) and (c), and the following two examples, illustrate the difference between masking and cropping).
# Both operations reduce object memory use and associated computational resources for subsequent analysis steps, and may be a necessary preprocessing step before creating attractive maps involving raster data.
#
# We will use two layers to illustrate raster cropping:
#
# -   The `srtm.tif` raster representing elevation, in meters above sea level, in south-western Utah: a **rasterio** file connection named `src_srtm` (see @fig-raster-crop (a))
# -   The `zion.gpkg` vector layer representing the Zion National Park boundaries (a `GeoDataFrame` named `zion`)
#
# Both target and cropping objects must have the same projection.
# Since it is easier and more precise to reproject vector layers, compared to rasters, we use the following expression to reproject (@sec-reprojecting-vector-geometries) the vector layer `zion` into the CRS of the raster `src_srtm`.
# <!-- jn: maybe reference to the CRS section/chapter -->
# <!-- md: done -->

zion = zion.to_crs(src_srtm.crs)

# To mask the image, i.e., convert all pixels which do not intersect with the `zion` polygon to "No Data", we use the [`rasterio.mask.mask`](https://rasterio.readthedocs.io/en/stable/api/rasterio.mask.html#rasterio.mask.mask) function.
#

out_image_mask, out_transform_mask = rasterio.mask.mask(
    src_srtm, 
    zion.geometry, 
    crop=False, 
    nodata=9999
)

# Note that we need to choose and specify a "No Data" value, within the valid range according to the data type.
# Since `srtm.tif` is of type `uint16` (how can we check?), we choose `9999` (a positive integer that is guaranteed not to occur in the raster).
# Also note that **rasterio** does not directly support **geopandas** data structures, so we need to pass a "collection" of **shapely** geometries: a `GeoSeries` (see below) or a `list` of **shapely** geometries (see next example) both work.
# <!-- jn: (see below) or (see above) -->
# The output consists of two objects.
# The first one is the `out_image` array with the masked values.

out_image_mask

# The second one is a new transformation matrix `out_transform`.

out_transform_mask

# Note that masking (without cropping!) does not modify the raster extent.
# Therefore, the new transform is identical to the original (`src_srtm.transform`).
#
# Unfortunately, the `out_image` and `out_transform` objects do not contain any information indicating that `9999` represents "No Data".
# To associate the information with the raster, we must write it to file along with the corresponding metadata.
# For example, to write the masked raster to file, we first need to modify the "No Data" setting in the metadata.

dst_kwargs = src_srtm.meta
dst_kwargs.update(nodata=9999)
dst_kwargs

# Then we can write the masked raster to file with the updated metadata object.

new_dataset = rasterio.open('output/srtm_masked.tif', 'w', **dst_kwargs)
new_dataset.write(out_image_mask)
new_dataset.close()

# Now we can re-import the raster and check that the "No Data" value is correctly set.

src_srtm_mask = rasterio.open('output/srtm_masked.tif')

# The `.meta` property contains the `nodata` entry.
# Now, any relevant operation (such as plotting) will take "No Data" into account.

src_srtm_mask.meta

# The related operation, cropping, reduces the raster extent to the extent of the vector layer:
#
# -   To just crop, *without* masking, we can derive the bounding box polygon of the vector layer, and then crop using that polygon, also combined with `crop=True` (@fig-raster-crop (c))
# -   To crop *and* mask, we can use `rasterio.mask.mask`, same as above for masking, just setting `crop=True` instead of the default `crop=False` (@fig-raster-crop (d))
#
# For the example of cropping only, the extent polygon of `zion` can be obtained as a `shapely` geometry object using the `.unary_union.envelope` property(@fig-zion-bbox).

#| label: fig-zion-bbox
#| fig-cap: Bounding box `'Polygon'` geometry of the `zion` layer
bb = zion.unary_union.envelope
bb

# The extent can now be used for masking.
# Here, we are also using the `all_touched=True` option so that pixels partially overlapping with the extent are also included in the output.

out_image_crop, out_transform_crop = rasterio.mask.mask(
    src_srtm, 
    [bb], 
    crop=True, 
    all_touched=True, 
    nodata=9999
)

# <!-- jn: why [bb] and not bb? -->
# Finally, we can perform crop and mask operations, using `rasterio.mask.mask` with `crop=True`.
# When writing to file, it is now crucial to update the transform and dimensions, since they were modified as a result of cropping.
# Also note that `out_image_mask_crop` is a three-dimensional array (even tough it has one band in this case), so the number of rows and columns are in `.shape[1]` and `.shape[2]` (rather than `.shape[0]` and `.shape[1]`), respectively.
# <!-- jn: why? -->
# <!-- jn: maybe split the code below into two chunks and describe them separately...? -->

out_image_mask_crop, out_transform_mask_crop = rasterio.mask.mask(
    src_srtm, 
    zion.geometry, 
    crop=True, 
    nodata=9999
)
dst_kwargs = src_srtm.meta
dst_kwargs.update({
    'nodata': 9999,
    'transform': out_transform_mask_crop,
    'width': out_image_mask_crop.shape[2],
    'height': out_image_mask_crop.shape[1]
})
new_dataset = rasterio.open('output/srtm_masked_cropped.tif', 'w', **dst_kwargs)
new_dataset.write(out_image_mask_crop)
new_dataset.close()
src_srtm_mask_crop = rasterio.open('output/srtm_masked_cropped.tif')

out_image_mask_crop.shape

# @fig-raster-crop shows the original raster, and the all of the masked and cropped results.

#| label: fig-raster-crop
#| fig-cap: Raster masking and cropping
#| layout-ncol: 2
#| fig-subcap: 
#| - Original
#| - Masked
#| - Cropped
#| - Masked+Cropped
# Original
fig, ax = plt.subplots(figsize=(3.5, 3.5))
rasterio.plot.show(src_srtm, ax=ax)
zion.plot(ax=ax, color='none', edgecolor='black');
# Masked
fig, ax = plt.subplots(figsize=(3.5, 3.5))
rasterio.plot.show(src_srtm_mask, ax=ax)
zion.plot(ax=ax, color='none', edgecolor='black');
# Cropped
fig, ax = plt.subplots(figsize=(3.5, 3.5))
rasterio.plot.show(out_image_crop, transform=out_transform_crop, ax=ax)
zion.plot(ax=ax, color='none', edgecolor='black');
# Masked+Cropped
fig, ax = plt.subplots(figsize=(3.5, 3.5))
rasterio.plot.show(src_srtm_mask_crop, ax=ax)
zion.plot(ax=ax, color='none', edgecolor='black');

# ## Raster extraction {#sec-raster-extraction}
#
# Raster extraction is the process of identifying and returning the values associated with a 'target' raster at specific locations, based on a (typically vector) geographic 'selector' object.
# The reverse of raster extraction---assigning raster cell values based on vector objects---is rasterization, described in @sec-rasterization.
#
# In the following examples, we use a package called **rasterstats**, which is specifically aimed at extracting raster values:
#
# -   To *points* (@sec-extraction-to-points) or to *lines* (@sec-extraction-to-lines), via the `rasterstats.point_query` function
# -   To *polygons* (@sec-extraction-to-polygons), via the `rasterstats.zonal_stats` function
#
# ### Extraction to points {#sec-extraction-to-points}
#
# The simplest type of raster extraction is getting the values of raster cells at specific points.
# To demonstrate extraction to points, we will use `zion_points`, which contains a sample of 30 locations within the Zion National Park (@fig-zion-points).

#| label: fig-zion-points
#| fig-cap: 30 point locations within the Zion National Park, with elevation in the background
fig, ax = plt.subplots()
rasterio.plot.show(src_srtm, ax=ax)
zion_points.plot(ax=ax, color='black');

# The following expression extracts elevation values from `srtm.tif` according to `zion_points`, using `rasterstats.point_query`.

result = rasterstats.point_query(
    zion_points, 
    src_srtm.read(1), 
    nodata = src_srtm.nodata, 
    affine = src_srtm.transform,
    interpolate='nearest'
)

# <!-- jn: explain the above arguments -->
#
# The resulting object is a `list` of raster values, corresponding to `zion_points`.
# For example, here are the elevations of the first five points.

result[:5]

# To get a `GeoDataFrame` with the original points geometries (and other attributes, if any), as well as the extracted raster values, we can assign the extraction result into a new column.

zion_points['elev'] = result
zion_points

# <!-- jn: what with multilayer raster? -->
#
# ### Extraction to lines {#sec-extraction-to-lines}
#
# Raster extraction is also applicable with line selectors.
# The typical line extraction algorithm is to extract one value for each raster cell touched by a line.
# However, this particular approach is not recommended to obtain values along the transects, as it is hard to get the correct distance between each pair of extracted raster values.
#
# For line extraction, a better approach is to split the line into many points (at equal distances along the line) and then extract the values for these points using the "extraction to points" technique (@sec-extraction-to-points).
# To demonstrate this, the code below creates (see @sec-vector-data for recap) `zion_transect`, a straight line going from northwest to southeast of the Zion National Park.

coords = [[-113.2, 37.45], [-112.9, 37.2]]
zion_transect = shapely.LineString(coords)
print(zion_transect)

# The utility of extracting heights from a linear selector is illustrated by imagining that you are planning a hike.
# The method demonstrated below provides an 'elevation profile' of the route (the line does not need to be straight), useful for estimating how long it will take due to long climbs.
#
# First, we need to create a layer consisting of points along our line (`zion_transect`), at specified intervals (e.g., `250`).
# To do that, we need to transform the line into a projected CRS (so that we work with true distances, in $m$), such as UTM.
# This requires going through a `GeoSeries`, as **shapely** geometries have no CRS definition nor concept of reprojection (see @sec-vector-layer-from-scratch).

zion_transect_utm = gpd.GeoSeries(zion_transect, crs=4326).to_crs(32612)
zion_transect_utm = zion_transect_utm.iloc[0]

# The printout of the new geometry shows this is still a straight line between two points, only with coordinates in a projected CRS.

print(zion_transect_utm)

# Next, we need to calculate the distances, along the line, where points are going to be generated, using [`np.arange`](https://numpy.org/doc/stable/reference/generated/numpy.arange.html).
# This is a numeric sequence starting at `0`, going up to line `.length`, in steps of `250` ($m$).

distances = np.arange(0, zion_transect_utm.length, 250)
distances[:7]  ## First 7 distance cutoff points

# The distances cutoffs are used to sample ("interpolate") points along the line.
# The **shapely** [`.interpolate`](https://shapely.readthedocs.io/en/stable/manual.html#object.interpolate) method is used to generate the points, which then are reprojected back to the geographic CRS of the raster (EPSG:`4326`).

zion_transect_pnt = [zion_transect_utm.interpolate(distance) for distance in distances]
zion_transect_pnt = gpd.GeoSeries(zion_transect_pnt, crs=32612).to_crs(src_srtm.crs)
zion_transect_pnt

# Finally, we extract the elevation values for each point in our transect and combine the information with `zion_transect_pnt` (after "promoting" it to a `GeoDataFrame`, to accommodate extra attributes), using the point extraction method shown earlier (@sec-extraction-to-points).
# We also attach the respective distance cutoff points `distances`.

result = rasterstats.point_query(
    zion_transect_pnt, 
    src_srtm.read(1), 
    nodata = src_srtm.nodata, 
    affine = src_srtm.transform,
    interpolate='nearest'
)
zion_transect_pnt = gpd.GeoDataFrame(geometry=zion_transect_pnt)
zion_transect_pnt['dist'] = distances
zion_transect_pnt['elev'] = result
zion_transect_pnt

# The information in `zion_transect_pnt`, namely the `'dist'` and `'elev'` attributes, can now be used to draw an elevation profile, as illustrated in @fig-zion-transect.

#| label: fig-zion-transect
#| fig-cap: Extracting a raster values profile to line 
#| layout-ncol: 2
#| fig-subcap: 
#| - Raster and a line transect
#| - Extracted elevation profile
# Raster and a line transect
fig, ax = plt.subplots()
rasterio.plot.show(src_srtm, ax=ax)
gpd.GeoSeries(zion_transect).plot(ax=ax, color='black')
zion.plot(ax=ax, color='none', edgecolor='white');
# Elevation profile
fig, ax = plt.subplots()
zion_transect_pnt.set_index('dist')['elev'].plot(ax=ax)
ax.set_xlabel('Distance (m)')
ax.set_ylabel('Elevation (m)');

# ### Extraction to polygons {#sec-extraction-to-polygons}
#
# The final type of geographic vector object for raster extraction is polygons.
# Like lines, polygons tend to return many raster values per polygon.
# For continuous rasters (@fig-raster-extract-to-polygon (a)), we typically want to generate summary statistics for raster values per polygon, for example to characterize a single region or to compare many regions.
# The generation of raster summary statistics, by polygons, is demonstrated in the code below using `rasterstats.zonal_stats`, which creates a list of summary statistics (in this case a list of length 1, since there is just one polygon).

result = rasterstats.zonal_stats(
    zion, 
    src_srtm.read(1), 
    nodata = src_srtm.nodata, 
    affine = src_srtm.transform, 
    stats = ['mean', 'min', 'max']
)
result

# Transformation of the `list` to a `DataFrame` (e.g., to attach the derived attributes to the original polygon layer), is straightforward with the `pd.DataFrame` constructor.

pd.DataFrame(result)

# Because there is only one polygon in the example, a `DataFrame` with a single row is returned.
# However, if `zion` was composed of more than one polygon, we would accordingly get more rows in the `DataFrame`.
# The result provides useful summaries, for example that the maximum height in the park is around `2661` $m$ above see level.
#
# Note the `stats` argument, where we determine what type of statistics are calculated per polygon.
# Possible values other than `'mean'`, `'min'`, `'max'` are:
#
# -   `'count'`---The number of valid (i.e., excluding "No Data") pixels
# -   `'nodata'`---The number of pixels with 'No Data"
# -   `'majority'`---The most frequently occurring value
# -   `'median'`---The median value
#
# See the [documentation](https://pythonhosted.org/rasterstats/manual.html#statistics) of `rasterstats.zonal_stats` for the complete list.
# Additionally, the `rasterstats.zonal_stats` function accepts user-defined functions for calculating any custom statistics.
#
# To count occurrences of categorical raster values within polygons (@fig-raster-extract-to-polygon (b)), we can use masking (@sec-raster-cropping) combined with `np.unique`, as follows.

out_image, out_transform = rasterio.mask.mask(
    src_nlcd, 
    zion.geometry.to_crs(src_nlcd.crs), 
    crop=False, 
    nodata=9999
)
counts = np.unique(out_image, return_counts=True)
counts

# According to the result, for example, pixel value `2` ("Developed" class) appears in `4205` pixels within the Zion polygon.
#
# @fig-raster-extract-to-polygon illustrates the two types of raster extraction to polygons described above.

#| label: fig-raster-extract-to-polygon
#| fig-cap: Sample data used for continuous and categorical raster extraction to a polygon
#| layout-ncol: 2
#| fig-subcap: 
#| - Continuous raster
#| - Categorical raster
# Continuous raster
fig, ax = plt.subplots()
rasterio.plot.show(src_srtm, ax=ax)
zion.plot(ax=ax, color='none', edgecolor='black');
# Categorical raster
fig, ax = plt.subplots()
rasterio.plot.show(src_nlcd, ax=ax, cmap='Set3')
zion.to_crs(src_nlcd.crs).plot(ax=ax, color='none', edgecolor='black');

# <!-- jn: what is the state of plotting categorical rasters? can it read the color palette from a file? -->
#
# ## Rasterization {#sec-rasterization}
#
# <!-- jn: intro is missing -->
#
# ### Rasterizing points {#sec-rasterizing-points}
#
# Rasterization is the conversion of vector objects into their representation in raster objects.
# Usually, the output raster is used for quantitative analysis (e.g., analysis of terrain) or modeling.
# As we saw in @sec-spatial-class, the raster data model has some characteristics that make it conducive to certain methods.
# Furthermore, the process of rasterization can help simplify datasets because the resulting values all have the same spatial resolution: rasterization can be seen as a special type of geographic data aggregation.
#
# The **rasterio** package contains the [`rasterio.features.rasterize`](https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html#rasterio.features.rasterize) function for doing this work.
# To make it happen, we need to have the "template" grid definition, i.e., the "template" raster defining the extent, resolution and CRS of the output, in the `out_shape` (the output dimensions) and `transform` (the transformation matrix) arguments of `rasterio.features.rasterize`.
# In case we have an existing template raster, we simply need to query its `.shape` and `.transform`.
# On the other hand, if we need to create a custom template, e.g., covering the vector layer extent with specified resolution, there is some extra work to calculate both of these objects (see next example).
#
# Furthermore, the `rasterio.features.rasterize` function requires the input vector shapes in the form of a generator of `(geom,value)` tuples, where:
#
# -   `geom` is the given geometry (**shapely** geometry object)
# -   `value` is the value to be "burned" into pixels coinciding with the geometry (`int` or `float`)
#
# Again, this will be made clear in the next example.
#
# The geographic resolution of the "template" raster has a major impact on the results: if it is too low (cell size is too large), the result may miss the full geographic variability of the vector data; if it is too high, computational times may be excessive.
# There are no simple rules to follow when deciding an appropriate geographic resolution, which is heavily dependent on the intended use of the results.
# Often the target resolution is imposed on the user, for example when the output of rasterization needs to be aligned to the existing raster.
#
# To demonstrate rasterization in action, we will use a template raster that has the same extent and CRS as the input vector data `cycle_hire_osm_projected` (a dataset on cycle hire points in London, illustrated in @fig-rasterize-points (a)) and a spatial resolution of 1000 $m$.
# First, we take the vector layer and transform it to a projected CRS:

cycle_hire_osm_projected = cycle_hire_osm.to_crs(27700)

# Next, we need to calculate the `out_shape` and `transform` of our template raster.
# To calculate the transform, we combine the top-left corner of the `cycle_hire_osm_projected` bounding box with the required resolution (e.g., 1000 $m$):

bounds = cycle_hire_osm_projected.total_bounds
res = 1000
transform = rasterio.transform.from_origin(
    west=bounds[0], 
    north=bounds[3], 
    xsize=res, 
    ysize=res
)
transform

# To calculate the `out_shape`, we divide the x-axis and y-axis extent by the resolution, and take the ceiling of the results:

rows = math.ceil((bounds[3] - bounds[1]) / res)
cols = math.ceil((bounds[2] - bounds[0]) / res)
shape = (rows, cols)
shape

# Now, we can rasterize.
# Rasterization is a very flexible operation: the results depend not only on the nature of the template raster, but also on the type of input vector (e.g., points, polygons), the pixel "activation" method, and the function applied when there is more than one match.
#
# To illustrate this flexibility, we will try three different approaches to rasterization (@fig-rasterize-points (b)-(d)).
# First, we create a raster representing the presence or absence of cycle hire points (known as presence/absence rasters).
# In this case, we transfer the value of `1` to all pixels where at least one point falls in.
# To transform the point `GeoDataFrame` into a generator of `shapely` geometries and the (fixed) values, we use the following expression.
# <!-- jn: maybe explain the code below in more detail? -->
# <!-- jn: also maybe use a different name than g? -->

g = ((g, 1) for g in cycle_hire_osm_projected.geometry.to_list())
g

# Then, the rasterizing expression takes the generator `g`, the template `shape` and `transform` as arguments.

#| output: false
ch_raster1 = rasterio.features.rasterize(
    shapes=g, 
    out_shape=shape, 
    transform=transform
)
ch_raster1

# The result `ch_raster1` is an `ndarray` with the burned values of `1` where the pixel coincides with at least one point, and `0` in "unaffected" pixels.
#
# To count the number of bike hire stations, we can use the fixed value of `1` combined with the `merge_alg=rasterio.enums.MergeAlg.add`, which means that multiple values burned into the same pixel are *summed*, rather than replaced keeping last (the default).
# <!--jn: rasterio.enums.MergeAlg.add definetely needs more explanation (maybe as a block)...-->

#| output: false
g = ((g, 1) for g in cycle_hire_osm_projected.geometry.to_list())
ch_raster2 = rasterio.features.rasterize(
    shapes=g,
    out_shape=shape,
    transform=transform,
    merge_alg=rasterio.enums.MergeAlg.add
)
ch_raster2

# The new output, `ch_raster2`, shows the number of cycle hire points in each grid cell.
# The cycle hire locations have different numbers of bicycles described by the capacity variable, raising the question, what is the capacity in each grid cell?
# To calculate that, we must sum the field (`'capacity'`) rather than the fixed values of `1`.
# This requires using an expanded generator of geometries and values, where we (1) extract both geometries and attribute values, and (2) filter out "No Data" values, which can be done as follows.
# <!-- jn: I think the code below should be explained in more detail... -->

#| output: false
g = ((g, v) for g, v in cycle_hire_osm_projected[['geometry', 'capacity']] \
        .dropna(subset='capacity')
        .to_numpy() \
        .tolist())
ch_raster3 = rasterio.features.rasterize(
    shapes=g,
    out_shape=shape,
    transform=transform,
    merge_alg=rasterio.enums.MergeAlg.add
)
ch_raster3

# The result `ch_raster3` shows the total capacity of cycle hire points in each grid cell.
#
# The input point layer `cycle_hire_osm_projected` and the three variants of rasterizing it `ch_raster1`, `ch_raster2`, and `ch_raster3` are shown in @fig-rasterize-points.

#| label: fig-rasterize-points
#| fig-cap: Original data and three variants of point rasterization
#| layout-ncol: 2
#| fig-subcap: 
#| - Input points
#| - Presence/Absence
#| - Point counts
#| - Summed attribute values
# Input points
fig, ax = plt.subplots()
cycle_hire_osm_projected.plot(column='capacity', ax=ax);
# Presence/Absence
fig, ax = plt.subplots()
rasterio.plot.show(ch_raster1, transform=transform, ax=ax);
# Point counts
fig, ax = plt.subplots()
rasterio.plot.show(ch_raster2, transform=transform, ax=ax);
# Summed attribute values
fig, ax = plt.subplots()
rasterio.plot.show(ch_raster3, transform=transform, ax=ax);

# ### Rasterizing lines and polygons {#sec-rasterizing-lines-and-polygons}
#
# Another dataset based on California's polygons and borders (created below) illustrates rasterization of lines.
# There are three preliminary steps.
# First, we subset the California polygon.

california = us_states[us_states['NAME'] == 'California']
california

# Second, we "cast" the polygon into a `'MultiLineString'` geometry, using the [`.boundary`](https://geopandas.org/en/stable/docs/reference/api/geopandas.GeoSeries.boundary.html) property that `GeoSeries` have.

california_borders = california.geometry.boundary
california_borders

# Third, we create a template raster with a resolution of a `0.5` degree, using the same approach as in @sec-rasterizing-points.

bounds = california_borders.total_bounds
res = 0.5
transform = rasterio.transform.from_origin(
    west=bounds[0], 
    north=bounds[3], 
    xsize=res, 
    ysize=res
)
rows = math.ceil((bounds[3] - bounds[1]) / res)
cols = math.ceil((bounds[2] - bounds[0]) / res)
shape = (rows, cols)
shape

# Finally, we rasterize `california_borders` based on the calculated template's `shape` and `transform`.
# When considering line or polygon rasterization, one useful additional argument is `all_touched`.
# By default it is `False`, but when changed to `True`---all cells that are touched by a line or polygon border get a value.
# Line rasterization with `all_touched=True` is demonstrated in the code below (@fig-rasterize-lines-polygons, left).
# We are also using `fill=np.nan` to set "background" values as "No Data".

california_raster1 = rasterio.features.rasterize(
    ((g, 1) for g in california_borders.to_list()),
    out_shape=shape,
    transform=transform,
    all_touched=True,
    fill=np.nan
)

# Compare it to a polygon rasterization, with `all_touched=False` (the default), which selects only raster cells whose centroids are inside the selector polygon, as illustrated in @fig-rasterize-lines-polygons (right).

california_raster2 = rasterio.features.rasterize(
    ((g, 1) for g in california.geometry.to_list()),
    out_shape=shape,
    transform=transform,
    fill=np.nan
)

# To illustrate which raster pixels are actually selected as part of rasterization, we also show them as points.
# This also requires the following code section to calculate the points, which we explain in @sec-spatial-vectorization.

ids = california_raster1.copy()
ids = np.arange(0, california_raster1.size) \
    .reshape(california_raster1.shape) \
    .astype(np.int32)
shapes = rasterio.features.shapes(ids, transform=transform)
pol = list(shapes)
pnt = [shapely.geometry.shape(i[0]).centroid for i in pol]
pnt = gpd.GeoSeries(pnt)

# @fig-rasterize-lines-polygons shows the input vector layer, the rasterization results, and the points `pnt`.

#| label: fig-rasterize-lines-polygons
#| fig-cap: Examples of line and polygon rasterization 
#| layout-ncol: 2
#| fig-subcap: 
#| - Line rasterization w/ `all_touched=True`
#| - Polygon rasterization w/ `all_touched=False`
# Line rasterization
fig, ax = plt.subplots()
rasterio.plot.show(california_raster1, transform=transform, ax=ax, cmap='Set3')
gpd.GeoSeries(california_borders).plot(ax=ax, edgecolor='darkgrey', linewidth=1)
pnt.plot(ax=ax, color='black', markersize=1);
# Polygon rasterization
fig, ax = plt.subplots()
rasterio.plot.show(california_raster2, transform=transform, ax=ax, cmap='Set3')
california.plot(ax=ax, color='none', edgecolor='darkgrey', linewidth=1)
pnt.plot(ax=ax, color='black', markersize=1);

# ## Spatial vectorization {#sec-spatial-vectorization}
#
# Spatial vectorization is the counterpart of rasterization (@sec-rasterization).
# It involves converting spatially continuous raster data into spatially discrete vector data such as points, lines or polygons.
# There are three standard methods to convert a raster to a vector layer, which we cover next:
#
# -   Raster to polygons (@sec-raster-to-polygons)---the most straightforward form of vectorization, converting raster cells to polygons, where each pixel is represented by a rectangular polygon
# -   Raster to points (@sec-raster-to-points)---has the additional step of calculating polygon centroids
# -   Raster to contours (@sec-raster-to-contours)
#
# Let us demonstrate all three in the given order.
#
# ### Raster to polygons {#sec-raster-to-polygons}
#
# The [`rasterio.features.shapes`](https://rasterio.readthedocs.io/en/stable/api/rasterio.features.html#rasterio.features.shapes) function can be used to access to the raster pixel as polygon geometries, as well as raster values.
# The returned object is a generator, which yields `geometry,value` pairs.
# The additional `transform` argument is used to yield true spatial coordinates of the polygons, which is usually what we want.
# <!-- jn: the above paragraph is not easy to read, maybe rephrase? -->
#
# For example, the following expression returns a generator named `shapes`, referring to the pixel polygons.

shapes = rasterio.features.shapes(
    rasterio.band(src_grain, 1), 
    transform=src_grain.transform
)
shapes

# We can generate all shapes at once into a `list` named `pol` with `list(shapes)`.

pol = list(shapes)

# Each element in `pol` is a `tuple` of length 2, containing the GeoJSON-like `dict`---representing the polygon geometry and the value of the pixel(s)---which comprise the polygon.
# For example, check the first element of `pol` with `pol[0]`.
#
# <!-- jn: maybe the next sentence as a block -->
# Note that each raster cell is converted into a polygon consisting of five coordinates, all of which are stored in memory (explaining why rasters are often fast compared with vectors!).
#
# To transform this `list` into a `GeoDataFrame`, we need few more steps of data reshaping.
# <!-- jn: add a sentence or two here... -->

# 'GeoSeries' with the polygons
geom = [shapely.geometry.shape(i[0]) for i in pol]
geom = gpd.GeoSeries(geom, crs=src_grain.crs)
# 'Series' with the values
values = [i[1] for i in pol]
values = pd.Series(values)
# Combine into a 'GeoDataFrame'
result = gpd.GeoDataFrame({'value': values, 'geometry': geom})
result

# The resulting polygon layer is shown in @fig-raster-to-polygons.
# As shown using the `edgecolor='black'` option, neighboring pixels sharing the same raster value are dissolved into larger polygons.
# The `rasterio.features.shapes` function does not offer a way to avoid this type of dissolving.
# One way to work around that is to convert an array with consecutive IDs, instead of the real values, to polygons, then extract the real values from the raster (see the example in @sec-raster-to-points).

#| label: fig-raster-to-polygons
#| fig-cap: '`grain.tif` converted to a polygon layer'
result.plot(column='value', edgecolor='black', legend=True);

# ### Raster to points {#sec-raster-to-points}
#
# To transform raster to points, we can use `rasterio.features.shapes`, same as in conversion to polygons (@sec-raster-to-points), only with the addition of the `.centroid` method to go from polygons to their centroids.
# However, to avoid dissolving nearby pixels, we will actually convert a raster with consecutive IDs, then extract the "true" values by point (it is not strictly necessary in this example, since the values of `elev.tif` are all unique).
#
# First, we create an `ndarray` with consecutive IDs, matching the shape of `elev.tif` raster values.

r = src_elev.read(1)
ids = r.copy()
ids = np.arange(0, r.size).reshape(r.shape).astype(np.int32)
ids

# Next, we use the `rasterio.features.shapes` function to create a point layer with the raster cell IDs.

shapes = rasterio.features.shapes(ids, transform=src_elev.transform)
pol = list(shapes)
geom = [shapely.geometry.shape(i[0]).centroid for i in pol]
geom = gpd.GeoSeries(geom, crs=src_elev.crs)
result = gpd.GeoDataFrame(geometry=geom)
result

# Finally, we extract (@sec-extraction-to-points) the `elev.tif` raster values to points, technically finalizing the raster-to-points conversion.

result['value'] = rasterstats.point_query(
    result, 
    r, 
    nodata = src_elev.nodata, 
    affine = src_elev.transform,
    interpolate='nearest'
)

# @fig-raster-to-points shows the input raster and the resulting point layer.

#| label: fig-raster-to-points
#| fig-cap: Raster and point representation of `elev.tif`
#| layout-ncol: 2
#| fig-subcap: 
#| - Input raster
#| - Points
# Input raster
fig, ax = plt.subplots()
result.plot(column='value', legend=True, ax=ax)
rasterio.plot.show(src_elev, ax=ax);
# Points
fig, ax = plt.subplots()
result.plot(column='value', legend=True, ax=ax)
rasterio.plot.show(src_elev, cmap='Greys', ax=ax);

# ### Raster to contours {#sec-raster-to-contours}
#
# Another common type of spatial vectorization is the creation of contour lines representing lines of continuous height or temperatures (*isotherms*), for example.
# We will use a real-world digital elevation model (DEM) because the artificial raster `elev.tif` produces parallel lines (task for the reader: verify this and explain why this happens).
# Plotting contour lines is straightforward, using the `contour=True` option of `rasterio.plot.show` (@fig-raster-contours1).

#| label: fig-raster-contours1
#| fig-cap: Displaying raster contours
fig, ax = plt.subplots()
rasterio.plot.show(src_dem, ax=ax)
rasterio.plot.show(
    src_dem, 
    ax=ax, 
    contour=True, 
    levels=np.arange(0,1200,50), 
    colors='black'
);

# Unfortunately, `rasterio` does not provide any way of extracting the contour lines in the form of a vector layer, for uses other than plotting.
#
# There are two possible workarounds:
#
# 1.  Using `gdal_contour` on the [command line](https://gdal.org/programs/gdal_contour.html) (see below), or through its Python interface [**osgeo**](https://gis.stackexchange.com/questions/360431/how-can-i-create-contours-from-geotiff-and-python-gdal-rasterio-etc-into-sh)
# 2.  Writing a custom function to export contour coordinates generated by, e.g., [**matplotlib**](https://www.tutorialspoint.com/how-to-get-coordinates-from-the-contour-in-matplotlib) or [**skimage**](https://gis.stackexchange.com/questions/268331/how-can-i-extract-contours-from-a-raster-with-python)
#
# We demonstrate the first approach, using `gdal_contour`.
# Although we deviate from the Python-focused approach towards more direct interaction with GDAL, the benefit of `gdal_contour` is the proven algorithm, customized to spatial data, and with many relevant options.
# Both the `gdal_contour` program (along with other GDAL programs) and its **osgeo** Python wrapper, should already be installed on your system since GDAL is a dependency of **rasterio**.
# Using the command line pathway, generating 50 $m$ contours of the `dem.tif` file can be done as follows.

#| eval: false
os.system('gdal_contour -a elev data/dem.tif output/dem_contour.gpkg -i 50.0')

# Like all GDAL programs (also see `gdaldem` example in @sec-focal-operations), `gdal_contour` works with files.
# Here, the input is the `data/dem.tif` file and the result is exported to the `output/dem_contour.gpkg` file.
#
# To illustrate the result, let's read the resulting `dem_contour.gpkg` layer back into the Python environment.
# Note that the layer contains an attribute named `'elev'` (as specified using `-a elev`) with the contour elevation values.

contours1 = gpd.read_file('output/dem_contour.gpkg')
contours1

# @fig-raster-contours2 shows the input raster and the resulting contour layer.

#| label: fig-raster-contours2
#| fig-cap: Contours of the `dem.tif` raster, calculated using the `gdal_contour` program
fig, ax = plt.subplots()
rasterio.plot.show(src_dem, ax=ax)
contours1.plot(ax=ax, edgecolor='black');

# ## Distance to nearest geometry {#sec-distance-to-nearest-geometry}
#
# Calculating a raster of distances to the nearest geometry is an example of a "global" raster operation (@sec-global-operations-and-distances).
# To demonstrate it, suppose that we need to calculate a raster representing the distance to the nearest coast in New Zealand.
# This example also wraps many of the concepts introduced in this chapter and in previous chapter, such as raster aggregation (@sec-raster-agg-disagg), raster conversion to points (@sec-raster-to-points), and rasterizing points (@sec-rasterizing-points).
#
# For the coastline, we will dissolve the New Zealand administrative division polygon layer and "extract" the boundary as a `'MultiLineString'` geometry.

coastline = gpd.GeoSeries(nz.unary_union, crs=nz.crs) \
    .to_crs(src_nz_elev.crs) \
    .boundary
coastline

# For a "template" raster, we will aggregate the New Zealand DEM, in the `nz_elev.tif` file, to 5 times coarser resolution.
# The code section below follows the aggeregation example in @sec-raster-agg-disagg, then replaces the original (aggregated) values with unique IDs, which is a preliminary step when converting to points, as explained in @sec-raster-to-points.
# Finally, we also replace "erase" (i.e., replace with `np.nan`) IDs which were `np.nan` in the aggregated elevation raster, i.e., beyond the land area of New Zealand.
# <!-- jn: the last sentence could be rephrased... -->

factor = 0.2
# Reading aggregated array
r = src_nz_elev.read(1,
    out_shape=(
        int(src_nz_elev.height * factor),
        int(src_nz_elev.width * factor)
        ),
    resampling=rasterio.enums.Resampling.average
)
# Updating the transform
new_transform = src_nz_elev.transform * src_nz_elev.transform.scale(
    (src_nz_elev.width / r.shape[1]),
    (src_nz_elev.height / r.shape[0])
)
# Generating unique IDs per cell
ids = r.copy()
ids = np.arange(0, r.size).reshape(r.shape).astype(np.float32)
# "Erasing" irrelevant IDs
ids[np.isnan(r)] = np.nan
ids

# The result is an array named `ids` with the IDs, and the corresponding `new_transform`, as plotted in @fig-raster-distances1.

# +
#| label: fig-raster-distances1
#| fig-cap: Template with cell IDs to calculate distance to nearest geometry

fig, ax = plt.subplots()
rasterio.plot.show(ids, transform=new_transform, ax=ax)
gpd.GeoSeries(coastline).plot(ax=ax, edgecolor='black');
# -

# To calculate distances, we must convert each pixel to a vector (point) geometry.
# For this purpose, we use the technique demonstrated in @sec-raster-to-points.

shapes = rasterio.features.shapes(ids, transform=new_transform)
pol = list(shapes)
pnt = [shapely.geometry.shape(i[0]).centroid for i in pol]

# The result `pnt` is a `list` of `shapely` geometries, representing raster cell centroids (excluding `np.nan` pixels):
#
# Now we can calculate the corresponding `list` of distances, using the `.distance` method from **shapely**:

distances = [(i, i.distance(coastline)) for i in pnt]
distances[0]

# Finally, we rasterize (see @sec-rasterizing-points) the distances into our raster template.

image = rasterio.features.rasterize(
    distances,
    out_shape=ids.shape,
    dtype=np.float_,
    transform=new_transform,
    fill=np.nan
)
image

# <!-- jn: there is a file path in the code output... can we remove it? -->
#
# The final result, a raster of distances to the nearest coastline, is shown in @fig-raster-distances2.

#| label: fig-raster-distances2
#| fig-cap: Distance to nearest coastline in New Zealand
fig, ax = plt.subplots()
rasterio.plot.show(image, transform=new_transform, ax=ax)
gpd.GeoSeries(coastline).plot(ax=ax, edgecolor='black');

# ## Exercises
