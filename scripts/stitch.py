import json
import os
import os.path
import glob
from PIL import Image, ImageFilter
import numpy as np

version = "../out/mapgen/versions/2024-04-10_a"

with open(f"{version}/worldMapDefinitions.json") as f:
    defs = json.load(f)
    jagex_def_ids = [d["fileId"] for d in defs]

with open("user_map_defs.json") as f:
    user_defs = json.load(f)

# Allow to overwrite jagex-defined maps' region lists
# Useful to avoid black regions in gielinor surface
for i, user_def in enumerate(user_defs):
    def_id = user_def["fileId"]

    if def_id in jagex_def_ids:
        def_index = jagex_def_ids.index(def_id)
        defs[def_index]["regionList"] = user_def["regionList"]

    else:
        defs.append(user_def)

with open(f"{version}/minimapIcons.json") as f:
    icons = json.load(f)

iconSprites = {}
for file in glob.glob(f"{version}/icons/*.png"):
    print(file)
    spriteId = int(file.split("/")[-1][:-4])
    iconSprites[spriteId] = Image.open(file)

overallXLow = 999
overallXHigh = 0
overallYLow = 999
overallYHigh = 0
for file in glob.glob(f"{version}/tiles/base/*.png"):
    filename = file.split("/")[-1]
    filename = filename.replace(".png", "")
    plane, x, y = map(int, filename.split("_"))
    overallYHigh = max(y, overallYHigh)
    overallYLow = min(y, overallYLow)
    overallXHigh = max(x, overallXHigh)
    overallXLow = min(x, overallXLow)

defs.append(
    {
        "name": "debug",
        "mapId": -1,
        "regionList": [
            {
                "xLowerLeft": overallXLow,
                "yUpperRight": overallYHigh,
                "yLowerRight": overallYLow,
                "yLowerLeft": overallYLow,
                "numberOfPlanes": 4,
                "xUpperLeft": overallXLow,
                "xUpperRight": overallXHigh,
                "yUpperLeft": overallYHigh,
                "plane": 0,
                "xLowerRight": overallXHigh,
            }
        ],
    }
)


def mkdir_p(path):
    try:
        os.makedirs(os.path.dirname(path))
    except OSError as exc:
        pass


def getBounds(regionList):
    lowX, lowY, highX, highY = 9999, 9999, 0, 0
    planes = 0
    for region in regionList:
        if "xLowerLeft" in region:  # typeA
            lowX = min(lowX, region["xUpperLeft"])
            highX = max(highX, region["xUpperRight"])
            lowY = min(lowY, region["yLowerLeft"])
            highY = max(highY, region["yUpperLeft"])
            planes = max(planes, region["numberOfPlanes"])
        elif "newX" in region:
            lowX = min(lowX, region["newX"])
            highX = max(highX, region["newX"])
            lowY = min(lowY, region["newY"])
            highY = max(highY, region["newY"])
            planes = max(planes, region["numberOfPlanes"])
        elif "xLow" in region:
            lowX = min(lowX, region["xLow"])
            highX = max(highX, region["xHigh"])
            lowY = min(lowY, region["yLow"])
            highY = max(highY, region["yHigh"])
            planes = max(planes, region["numberOfPlanes"])
        else:
            raise ValueError(region)
    return lowX, highX, lowY, highY, planes


def pointInsideBox(
    position,
    plane,
    lowX,
    highX,
    lowY,
    highY,
    chunk_lowX,
    chunk_highX,
    chunk_lowY,
    chunk_highY,
    allPlanes,
):
    x = position["x"]
    y = position["y"]
    z = position["z"]
    lowX = lowX * 64 + chunk_lowX * 8
    lowY = lowY * 64 + chunk_lowY * 8
    highX = highX * 64 + chunk_highX * 8 + 7
    highY = highY * 64 + chunk_highY * 8 + 7
    return (
        ((plane == 0) or (plane == z))
        and x >= lowX
        and x <= highX
        and y >= lowY
        and y <= highY
    )


def getIconsInsideArea(
    plane,
    lowX,
    highX,
    lowY,
    highY,
    chunk_lowX=0,
    chunk_highX=7,
    chunk_lowY=0,
    chunk_highY=7,
    dx=0,
    dy=0,
    dz=0,
    allPlanes=False,
):
    valid = []
    for icon in icons:
        if pointInsideBox(
            icon["position"],
            plane,
            lowX,
            highX,
            lowY,
            highY,
            chunk_lowX,
            chunk_highX,
            chunk_lowY,
            chunk_highY,
            allPlanes,
        ):
            pos = icon["position"]
            icon = [pos["x"] + dx, pos["y"] + dy, icon["spriteId"]]
            valid.append(icon)
    return valid


def allBlack(im):
    data = np.asarray(im.convert("RGBA"))
    return np.count_nonzero(data[:, :, :3]) == 0


PADDING = 64
baseMaps = []
px_per_square = 4
for defn in defs:
    mapId = -1
    if "mapId" in defn:
        mapId = defn["mapId"]
    elif "fileId" in defn:
        mapId = defn["fileId"]
    lowX, highX, lowY, highY, planes = getBounds(defn["regionList"])
    bounds = [
        [lowX * 64 - PADDING, lowY * 64 - PADDING],
        [(highX + 1) * 64 + PADDING, (highY + 1) * 64 + PADDING],
    ]
    # bounds = [[0, 0], [12800, 12800]]
    if mapId < 1:
        center = [2496, 3328]
    elif "position" in defn:
        center = [defn["position"]["x"], defn["position"]["y"]]
    else:
        print("cent")
        center = [(lowX + highX + 1) * 32, (lowY + highY + 1) * 32]
    baseMaps.append(
        {
            "mapId": mapId,
            "name": defn["name"],
            "bounds": bounds,
            "center": center,
        }
    )
    overallHeight = (highY - lowY + 1) * px_per_square * 64
    overallWidth = (highX - lowX + 1) * px_per_square * 64

    plane0Map = None
    for plane in range(planes):
        print(mapId, plane)
        validIcons = []
        # Canvas is this map defn plus 1-region border
        im = Image.new(
            "RGB",
            (
                overallWidth + PADDING * px_per_square * 2,
                overallHeight + PADDING * px_per_square * 2,
            ),
        )

        # All maps may be offset in the z (plane) direction, only some in x/y
        for region in defn["regionList"]:
            # These maps may be cartographically offset by some # regions
            if "xLowerLeft" in region:
                # `plane` is cartographically what plane this image will be on
                # `og_plane` is its actual z location
                og_base_plane = region["plane"]
                og_plane = og_base_plane + plane

                oldLowX = region["xLowerLeft"]
                oldHighX = region["xLowerRight"]
                oldLowY = region["yLowerLeft"]
                oldHighY = region["yUpperLeft"]
                newLowX = region["xUpperLeft"]
                newHighX = region["xUpperRight"]
                newLowY = region["yLowerRight"]
                newHighY = region["yUpperRight"]

                if oldLowX != newLowX or oldHighX != newHighX:
                    print("Offset X")
                if oldLowY != newLowY or oldHighY != newHighY:
                    print("Offset Y")

                validIcons.extend(
                    getIconsInsideArea(
                        og_plane,
                        oldLowX,
                        oldHighX,
                        oldLowY,
                        oldHighY,
                        allPlanes=plane == 0,
                    )
                )
                for x in range(oldLowX, oldHighX + 1):
                    for y in range(oldLowY, oldHighY + 1):
                        filename = f"{version}/tiles/base/{og_plane}_{x}_{y}.png"
                        if os.path.exists(filename):
                            square = Image.open(filename)
                            imX = (x - lowX + newLowX - oldLowX) * px_per_square * 64
                            imY = (highY - y) * px_per_square * 64
                            im.paste(square, box=(imX + 256, imY + 256))

            # Regions in these maps may be offset by some # chunks
            elif "chunk_oldXLow" in region:
                og_base_plane = region["oldPlane"]
                og_plane = og_base_plane + plane
                plane_offset = 0 - og_base_plane

                region_low_x = region["oldX"]
                region_low_y = region["oldY"]
                region_offset_x = (region["newX"] - region_low_x) * 64
                region_offset_y = (region["newY"] - region_low_y) * 64

                chunk_low_x = region["chunk_oldXLow"]
                chunk_high_x = region["chunk_oldXHigh"]
                chunk_low_y = region["chunk_oldYLow"]
                chunk_high_y = region["chunk_oldYHigh"]
                chunk_offset_x = (region["chunk_newXLow"] - chunk_low_x) * 8
                chunk_offset_y = (region["chunk_newYLow"] - chunk_low_y) * 8

                dx = region_offset_x + chunk_offset_x
                dy = region_offset_y + chunk_offset_y
                dz = plane_offset
                validIcons.extend(
                    getIconsInsideArea(
                        og_plane,
                        region_low_x,
                        region_low_x,
                        region_low_y,
                        region_low_y,
                        chunk_low_x,
                        chunk_high_x,
                        chunk_low_y,
                        chunk_high_y,
                        dx,
                        dy,
                        dz,
                        allPlanes=plane == 0,
                    )
                )

                filename = (
                    f"{version}/tiles/base/{og_plane}_{region_low_x}_{region_low_y}.png"
                )
                if os.path.exists(filename):
                    square = Image.open(filename)
                    cropped = square.crop(
                        (
                            chunk_low_x * 8 * px_per_square,
                            (8 - chunk_high_y - 1) * 8 * px_per_square,
                            (chunk_high_x + 1) * 8 * px_per_square,
                            (8 - chunk_low_y) * 8 * px_per_square,
                        )
                    )
                    imX = (region["newX"] - lowX) * px_per_square * 64 + region[
                        "chunk_newXLow"
                    ] * px_per_square * 8
                    imY = (highY - region["newY"]) * px_per_square * 64 + (
                        7 - region["chunk_newYHigh"]
                    ) * px_per_square * 8
                    im.paste(
                        cropped,
                        box=(
                            imX + PADDING * px_per_square,
                            imY + PADDING * px_per_square,
                        ),
                    )

            # These maps may include chunk-granular subsets of a region
            elif "chunk_xLow" in region:
                og_base_plane = region["oldPlane"]
                og_plane = og_base_plane + plane

                x_low = region["xLow"]
                y_low = region["yLow"]

                validIcons.extend(
                    getIconsInsideArea(
                        og_plane,
                        x_low,
                        region["xHigh"],
                        y_low,
                        region["yHigh"],
                        region["chunk_xLow"],
                        region["chunk_xHigh"],
                        region["chunk_yLow"],
                        region["chunk_yHigh"],
                        allPlanes=plane == 0,
                    )
                )
                filename = f"{version}/tiles/base/{og_plane}_{x_low}_{y_low}.png"
                if os.path.exists(filename):
                    square = Image.open(filename)
                    cropped = square.crop(
                        (
                            region["chunk_xLow"] * px_per_square * 8,
                            (8 - region["chunk_yHigh"] - 1) * px_per_square * 8,
                            (region["chunk_xHigh"] + 1) * px_per_square * 8,
                            (8 - region["chunk_yLow"]) * px_per_square * 8,
                        )
                    )
                    imX = (x_low - lowX) * px_per_square * 64 + region[
                        "chunk_xLow"
                    ] * px_per_square * 8
                    imY = (highY - y_low) * px_per_square * 64 + (
                        7 - region["chunk_yHigh"]
                    ) * px_per_square * 8
                    im.paste(
                        cropped,
                        box=(
                            imX + px_per_square * PADDING,
                            imY + px_per_square * PADDING,
                        ),
                    )

            # These maps are not offset in x/y
            elif "xLow" in region:
                og_base_plane = region["plane"]
                og_plane = og_base_plane + plane

                validIcons.extend(
                    getIconsInsideArea(
                        og_plane,
                        region["xLow"],
                        region["xHigh"],
                        region["yLow"],
                        region["yHigh"],
                        allPlanes=plane == 0,
                    )
                )
                for x in range(region["xLow"], region["xHigh"] + 1):
                    for y in range(region["yLow"], region["yHigh"] + 1):
                        filename = f"{version}/tiles/base/{og_plane}_{x}_{y}.png"
                        if os.path.exists(filename):
                            square = Image.open(filename)
                            imX = (x - lowX) * px_per_square * 64
                            imY = (highY - y) * px_per_square * 64
                            im.paste(square, box=(imX + 256, imY + 256))

            else:
                raise ValueError(region)

        if plane == 0:
            data = np.asarray(im.convert("RGB")).copy()
            data[(data == (255, 0, 255)).all(axis=-1)] = (0, 0, 0)
            im = Image.fromarray(data, mode="RGB")
            if planes > 1:
                plane0Map = im.convert("LA").filter(ImageFilter.GaussianBlur(radius=5))

        elif plane > 0:
            data = np.asarray(im.convert("RGBA")).copy()
            data[:, :, 3] = 255 * (data[:, :, :3] != (255, 0, 255)).all(axis=-1)
            mask = Image.fromarray(data, mode="RGBA")
            im = plane0Map.convert("RGBA")
            im.paste(mask, (0, 0), mask)

        for zoom in range(-3, 4):
            scalingFactor = 2.0**zoom / 2.0**2
            zoomedWidth = int(round(scalingFactor * im.width))
            zoomedHeight = int(round(scalingFactor * im.height))
            resample = Image.BILINEAR if zoom <= 1 else Image.NEAREST
            zoomed = im.resize((zoomedWidth, zoomedHeight), resample=resample)
            if zoom >= 0:
                for x, y, spriteId in validIcons:
                    sprite = iconSprites[spriteId]
                    width, height = sprite.size
                    imX = (
                        int(round((x - lowX * 64) * px_per_square * scalingFactor))
                        - width // 2
                        - 2
                    )
                    imY = (
                        int(
                            round(
                                ((highY + 1) * 64 - y) * px_per_square * scalingFactor
                            )
                        )
                        - height // 2
                        - 2
                    )
                    zoomed.paste(
                        sprite,
                        (
                            imX + int(round(256 * scalingFactor)),
                            int(round(imY + 256 * scalingFactor)),
                        ),
                        sprite,
                    )

            lowZoomedX = int((lowX - 1) * scalingFactor + 0.01)
            highZoomedX = int((highX + 0.9 + 1) * scalingFactor + 0.01)
            lowZoomedY = int((lowY - 1) * scalingFactor + 0.01)
            highZoomedY = int((highY + 0.9 + 1) * scalingFactor + 0.01)
            for x in range(lowZoomedX, highZoomedX + 1):
                for y in range(lowZoomedY, highZoomedY + 1):
                    coordX = int((x - (lowX - 1) * scalingFactor) * 256)
                    coordY = int((y - (lowY - 1) * scalingFactor) * 256)
                    cropped = zoomed.crop(
                        (
                            coordX,
                            zoomed.size[1] - coordY - 256,
                            coordX + 256,
                            zoomed.size[1] - coordY,
                        )
                    )
                    if not allBlack(cropped):
                        outfilename = f"{version}/tiles/rendered/{mapId}/{zoom}/{plane}_{x}_{y}.png"
                        mkdir_p(outfilename)
                        cropped.save(outfilename)
            # outfilename = "%s/tiles/rendered/%s/%s_%s_full.png" % (version, mapId, plane, zoom)
            # mkdir_p(outfilename)
            # zoomed.save(outfilename)
with open(f"{version}/basemaps.json", "w") as f:
    json.dump(baseMaps, f)
