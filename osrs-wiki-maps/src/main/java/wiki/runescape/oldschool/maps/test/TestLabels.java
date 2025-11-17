package wiki.runescape.oldschool.maps.test;

import java.io.File;
import java.util.List;
import lombok.extern.slf4j.Slf4j;
import net.runelite.cache.AreaManager;
import net.runelite.cache.WorldMapManager;
import net.runelite.cache.definitions.AreaDefinition;
import net.runelite.cache.definitions.WorldMapElementDefinition;
import net.runelite.cache.fs.Store;
import net.runelite.cache.region.Position;

@Slf4j
public class TestLabels
{
	public static void main(String[] args) throws Exception
	{
		String version = "2025-11-05_d";
		String cacheDir = String.format("./data/versions/%s", version);
		String cache = String.format("%s/cache", cacheDir);

		Store store = new Store(new File(cache));
		store.load();

		WorldMapManager worldMapManager = new WorldMapManager(store);
		AreaManager areas = new AreaManager(store);
		worldMapManager.load();
		areas.load();

		List<WorldMapElementDefinition> elements = worldMapManager.getElements();
		for (WorldMapElementDefinition element : elements)
		{
			AreaDefinition area = areas.getArea(element.getAreaDefinitionId());
			Position pos = element.getWorldPosition();
			if (area == null || area.getName() == null)
			{
				continue;
			}

			String areaLabelBad = area.getName();
			String areaLabel = areaLabelBad.replace("<br>", " ");

			log.info("|label:{},x:{},y:{}", areaLabel, pos.getX(), pos.getY());
		}
	}
}