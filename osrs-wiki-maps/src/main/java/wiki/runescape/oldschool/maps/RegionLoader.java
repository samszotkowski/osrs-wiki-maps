package wiki.runescape.oldschool.maps;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import net.runelite.cache.IndexType;
import net.runelite.cache.ObjectManager;
import net.runelite.cache.definitions.LocationsDefinition;
import net.runelite.cache.definitions.MapDefinition;
import net.runelite.cache.definitions.MapSquareDefinition;
import net.runelite.cache.definitions.ObjectDefinition;
import net.runelite.cache.definitions.WorldMapCompositeDefinition;
import net.runelite.cache.definitions.ZoneDefinition;
import net.runelite.cache.definitions.loaders.LocationsLoader;
import net.runelite.cache.definitions.loaders.MapLoader;
import net.runelite.cache.definitions.loaders.WorldMapCompositeLoader;
import net.runelite.cache.fs.Archive;
import net.runelite.cache.fs.ArchiveFiles;
import net.runelite.cache.fs.FSFile;
import net.runelite.cache.fs.Index;
import net.runelite.cache.fs.Storage;
import net.runelite.cache.fs.Store;
import net.runelite.cache.io.InputStream;
import net.runelite.cache.region.Location;
import net.runelite.cache.region.Position;
import net.runelite.cache.util.KeyProvider;

@Slf4j
public class RegionLoader extends net.runelite.cache.region.RegionLoader
{
	private static final int MAX_REGION = 32768;

	private final Store store;
	private final Index indexGeography;
	private final Index indexWorldmap;
	private final Index indexMinimap;
	private final KeyProvider keyProvider;
	private final ObjectManager objectManager;

	public RegionLoader(Store store, KeyProvider keyProvider, ObjectManager objectManager)
	{
		super(store, keyProvider);

		this.store = store;
		indexMinimap = store.getIndex(IndexType.MAPS);
		indexGeography = store.getIndex(IndexType.WORLDMAP_GEOGRAPHY);
		indexWorldmap = store.getIndex(IndexType.WORLDMAP);
		this.keyProvider = keyProvider;
		this.objectManager = objectManager;
	}

	@Override
	public void loadRegions() throws IOException
	{
		if (!super.getRegions().isEmpty())
		{
			return;
		}

		Storage storage = store.getStorage();

		HashMap<Integer, List<Location>> locsByRegion = new HashMap<>();
		HashMap<Integer, HashSet<Integer>> seenZonesByLevel = new HashMap<>();
		seenZonesByLevel.put(0, new HashSet<>());
		seenZonesByLevel.put(1, new HashSet<>());
		seenZonesByLevel.put(2, new HashSet<>());
		seenZonesByLevel.put(3, new HashSet<>());

		// Load overworld locations
		WorldMapCompositeLoader loader = new WorldMapCompositeLoader();
		Archive archive = indexWorldmap.findArchiveByName("compositemap");
		byte[] archiveData = storage.loadArchive(archive);
		ArchiveFiles files = archive.getFiles(archiveData);

		for (FSFile file : files.getFiles())
		{
			WorldMapCompositeDefinition worldMapDef = loader.load(file.getContents());

			for (MapSquareDefinition mapSquareDef : worldMapDef.getMapSquareDefinitions())
			{
				int archiveId = mapSquareDef.getGroupId();
				int fileId = mapSquareDef.getFileId();
				FSFile locFile = getFile(indexGeography, storage, archiveId, fileId);

				InputStream buffer = new InputStream(locFile.getContents());
				int mapType = buffer.readUnsignedByte();

				int mapsquareX = buffer.readUnsignedByte();  // == mapSquareDef.getDisplaySquareX()
				int mapsquareY = buffer.readUnsignedByte();  // == mapSquareDef.getDisplaySquareZ()
				int regionId = (mapSquareDef.getSourceSquareX() << 8) + mapSquareDef.getSourceSquareZ();

				if (!locsByRegion.containsKey(regionId))
				{
					locsByRegion.put(regionId, new ArrayList<>());
				}

				int minLevel = mapSquareDef.getMinLevel();

				LocationsDefinition locDef = loadLocationDefinitionWorldmap(regionId, buffer, mapType);
				for (Location loc : locDef.getLocations())
				{
					int x = loc.getPosition().getX();
					int y = loc.getPosition().getY();
					int z = loc.getPosition().getZ() + minLevel;
					locsByRegion.get(regionId).add(new Location(
						loc.getId(), loc.getType(), loc.getOrientation(), new Position(x, y, z)
					));

					// We want to draw map icons in actual location *and* on minLevel
					// because in-game world map draws all icons on minLevel
					ObjectDefinition objDef = objectManager.getObject(loc.getId());
					boolean isMapIcon = objDef.getMapAreaId() != -1;
					if (isMapIcon && z != minLevel)
					{
						locsByRegion.get(regionId).add(new Location(
							loc.getId(), loc.getType(), loc.getOrientation(), new Position(x, y, minLevel)
						));
					}

					int zoneId = getZoneId(mapsquareX, mapsquareY, x, y);
					seenZonesByLevel.get(z).add(zoneId);
				}
			}

			for (ZoneDefinition zoneDef : worldMapDef.getZoneDefinitions())
			{
				int archiveId = zoneDef.getGroupId();
				int fileId = zoneDef.getFileId();
				FSFile locFile = getFile(indexGeography, storage, archiveId, fileId);

				InputStream buffer = new InputStream(locFile.getContents());
				int mapType = buffer.readUnsignedByte();

				int mapsquareX = buffer.readUnsignedByte();  // == zoneDef.getDisplaySquareX()
				int mapsquareY = buffer.readUnsignedByte();  // == zoneDef.getDisplaySquareZ()
				int regionId = (zoneDef.getSourceSquareX() << 8) + zoneDef.getSourceSquareZ();

				if (!locsByRegion.containsKey(regionId))
				{
					locsByRegion.put(regionId, new ArrayList<>());
				}

				int offsetX = 8 * (zoneDef.getSourceZoneX() - zoneDef.getDisplayZoneX());
				int offsetY = 8 * (zoneDef.getSourceZoneZ() - zoneDef.getDisplayZoneZ());
				int minLevel = zoneDef.getMinLevel();

				LocationsDefinition locDef = loadLocationDefinitionWorldmap(regionId, buffer, mapType);
				for (Location loc : locDef.getLocations())
				{
					int x = loc.getPosition().getX() + offsetX;
					int y = loc.getPosition().getY() + offsetY;
					int z = loc.getPosition().getZ() + minLevel;
					locsByRegion.get(regionId).add(new Location(
						loc.getId(), loc.getType(), loc.getOrientation(), new Position(x, y, z)
					));

					ObjectDefinition objDef = objectManager.getObject(loc.getId());
					boolean isMapIcon = objDef.getMapAreaId() != -1;
					if (isMapIcon && z != minLevel)
					{
						locsByRegion.get(regionId).add(new Location(
							loc.getId(), loc.getType(), loc.getOrientation(), new Position(x, y, minLevel)
						));
					}

					int zoneId = getZoneId(mapsquareX, mapsquareY, x, y);
					seenZonesByLevel.get(z).add(zoneId);
				}
			}
		}

		for (int regionId = 0; regionId < MAX_REGION; ++regionId)
		{
			int mapsquareX = regionId >> 8;
			int mapsquareY = regionId & 0xFF;

			MapDefinition mapDef = loadMapDefinition(regionId, storage);
			if (mapDef != null)
			{
				List<Location> outLocs = new ArrayList<>();

				LocationsDefinition minimapLocs = loadLocationDefinitionMinimap(regionId, storage);
				if (minimapLocs != null)
				{
					for (Location loc : minimapLocs.getLocations())
					{
						int x = loc.getPosition().getX();
						int y = loc.getPosition().getY();
						int z = loc.getPosition().getZ();

						int zoneId = getZoneId(mapsquareX, mapsquareY, x, y);
						// If we already got locs from the worldmap data in this zone,
						// don't need to grab duplicates from minimap data.
						if (!seenZonesByLevel.get(z).contains(zoneId))
						{
							Position newPos = new Position(x, y, z);
							outLocs.add(new Location(loc.getId(), loc.getType(), loc.getOrientation(), newPos));
						}
					}
				}

				outLocs.addAll(locsByRegion.getOrDefault(regionId, Collections.emptyList()));

				LocationsDefinition outDef = new LocationsDefinition();
				outDef.setRegionX(regionId >> 8);
				outDef.setRegionY(regionId & 0xFF);
				outDef.setLocations(outLocs);

				loadRegion(regionId, mapDef, outDef);
			}
		}
	}

	private MapDefinition loadMapDefinition(int regionId, Storage storage) throws IOException
	{
		int x = regionId >> 8;
		int y = regionId & 0xFF;

		Archive mapArchive = indexMinimap.findArchiveByName("m" + x + "_" + y);

		if (mapArchive == null)
		{
			return null;
		}

		byte[] mapData = mapArchive.decompress(storage.loadArchive(mapArchive));
		return new MapLoader().load(x, y, mapData);
	}

	private LocationsDefinition loadLocationDefinitionWorldmap(int regionId, InputStream worldmapBuffer, int mapType) throws IOException
	{
		int x = regionId >> 8;
		int y = regionId & 0xFF;

		ArrayList<Location> locations = new ArrayList<>();

		if (mapType == 0)
		{
			locations.addAll(WorldmapLocations.loadMapSquare(worldmapBuffer));
		}
		else
		{
			int zoneX = worldmapBuffer.readUnsignedByte();
			int zoneY = worldmapBuffer.readUnsignedByte();
			locations.addAll(WorldmapLocations.loadZone(worldmapBuffer, zoneX, zoneY));
		}

		LocationsDefinition locDef = new LocationsDefinition();
		locDef.setRegionX(x);
		locDef.setRegionY(y);
		locDef.setLocations(locations);
		return locDef;
	}

	private LocationsDefinition loadLocationDefinitionMinimap(int regionId, Storage storage) throws IOException
	{
		int x = regionId >> 8;
		int y = regionId & 0xFF;

		Archive locArchive = indexMinimap.findArchiveByName("l" + x + "_" + y);
		int[] keys = keyProvider.getKey(regionId);

		if (locArchive == null || keys == null)
		{
			return null;
		}

		byte[] locDataMinimap = locArchive.decompress(storage.loadArchive(locArchive), keys);
		return new LocationsLoader().load(x, y, locDataMinimap);
	}

	private FSFile getFile(Index index, Storage storage, int archiveId, int fileId) throws IOException
	{
		Archive archive = index.getArchive(archiveId);
		ArchiveFiles files = archive.getFiles(storage.loadArchive(archive));
		for (FSFile file : files.getFiles())
		{
			if (file.getFileId() == fileId) {
				return file;
			}
		}
		return null;
	}

	private int getZoneId(int mapsquareX, int mapsquareY, int localX, int localY)
	{
		// localX and localY are coordinates relative to the mapsquare
		int zoneX = localX / 8 + mapsquareX * 8;
		int zoneY = localY / 8 + mapsquareY * 8;
		return 2048 * zoneX + zoneY;
	}
}