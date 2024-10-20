#!/usr/bin/env python3

"""
    Script to build Minecraft datapacks for the Big Globe mod
    ~~~~~~~~~~

    :copyright: (c) 2021 by Nicholas Murphy.
    :license: GPLv2, see LICENSE for more details.
"""


__author__ = "nmurphy101"
__version__ = '1.0.0-alpha'

import json
import os
import shutil
import sys
import toml
import zipfile


def main(jar_filename):
    """
    Main function to build a Minecraft bigglobe compatability datapack for a mod
    :param jar_filename: The filename of the mod jar file
    :return: None
    """

    # INITIAL MOD UNPACKING SECTION AND SETUP
    # Open the JAR file and extract all files and subdirectories
    jar_directory_filename = jar_filename.rstrip(".jar")
    with zipfile.ZipFile(f"./mods/{jar_filename}", 'r') as jar:
        jar.extractall(jar_directory_filename)

    # Check if a fabric.mod.json file exists in the jar_directory_filename directory
    if os.path.exists(f"{jar_directory_filename}/fabric.mod.json"):
        print(f"  - Fabric Mod Detected: fabric.mod.json file found")
        with open(f"{jar_directory_filename}/fabric.mod.json", "r") as f:
            fabric_mod_json = json.load(f)
        mod_name = fabric_mod_json['id']
    # Check if the mods.toml directory exists in the jar_directory_filename directory
    elif os.path.exists(f"{jar_directory_filename}/META-INF/mods.toml"):
        print(f"  - Forge Mod Detected: mods.toml found")
        with open(f"{jar_directory_filename}/META-INF/mods.toml", "r") as f:
            mods_toml = toml.load(f)
        mod_name = mods_toml['mods'][0]['modId']

    else:
        print(f"  - Could not find a mods.toml or fabric.mod.json file in the {jar_directory_filename} directory. Skipping")
        # remove the jar_directory_filename directory and all of it's contents
        shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
        return

    if mod_name == "bigglobe":
        print(f"  - Skipping {jar_directory_filename} as it is the Big Globe mod")
        # remove the jar_directory_filename directory and all of it's contents
        shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
        return

    # Get the mod directory path
    mod_directory = os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename)

    # Check if the mod_directory data directory exists
    if not os.path.exists(os.path.join(mod_directory, "data")):
        print(f"  - Could not find a data directory in the {jar_directory_filename} directory. Skipping")
        # remove the jar_directory_filename directory and all of it's contents
        shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
        return

    # create the new directory
    new_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), f"{mod_name}_compat_datapack")
    os.makedirs(new_dir, exist_ok=True)


    # PACK.MCMETA SECTION
    # create the pack.mcmeta file by loading a json file and modifying it's pack description to include the mod name
    with open("templates/pack_mcmeta_template.json", "r") as f:
        data = json.load(f)
    json_string = json.dumps(data, indent=4).replace("{MOD_NAME}", mod_name)
    pack_mcmeta = json.loads(json_string)

    with open(os.path.join(new_dir, "pack.mcmeta"), "w") as f:
        json.dump(pack_mcmeta, f, indent=4)

    # create the data directory
    data_dir = os.path.join(new_dir, "data", f"bigglobe_{mod_name}")
    os.makedirs(data_dir, exist_ok=True)


    # TAGS SECTION
    tags_modified = False
    # check if the mod_directory/data/{MOD_NAME}/worldgen/configured_feature directory exists
    if os.path.exists(os.path.join(mod_directory, "data", mod_name, "worldgen", "configured_feature")):
        # create the tags directory
        tags_dir = os.path.join(data_dir, "tags", "worldgen")
        os.makedirs(tags_dir, exist_ok=True)

        # create the configured_feature directory
        tags_configured_feature_dir = os.path.join(tags_dir, "configured_feature")
        os.makedirs(tags_configured_feature_dir, exist_ok=True)

        # create the overworld directory in the tags directory
        tags_overworld_dir = os.path.join(tags_configured_feature_dir, "overworld")
        os.makedirs(tags_overworld_dir, exist_ok=True)

        # create the ores.json file in the overworld directory by loading a json file and modifying it's values to include the
        # create the ores.json file by loading a json file and modifying it's "values" key to have an array of "bigglobe:overworld/ores/{ORE_NAME}" entries
        # where the ORE_NAME's are the filenames inside the mod directory's "data/{MOD_NAME}/worldgen/configured_feature/overworld" directory
        ore_titles = []
        with open("templates/tags_ores_template.json", "r") as template_f:
            tag_ores = json.load(template_f)

        for ore in os.listdir(os.path.join(mod_directory, "data", mod_name, "worldgen", "configured_feature")):
            ore_path = os.path.join(mod_directory, "data", mod_name, "worldgen", "configured_feature", ore)
            if os.path.isfile(ore_path):
                with open(os.path.join(mod_directory, "data", mod_name, "worldgen", "configured_feature", ore), "r") as ore_f:
                    data = json.load(ore_f)
                    #Check if the ore file is just for a separate dimension and skip it
                    data_type = data["type"].split(":")[0]
                    if data_type != "minecraft":
                        continue

                    try:
                        ore_targets = data["config"]["targets"]
                    except KeyError:
                        continue

                    for target in ore_targets:
                        try:
                            ore_name = target["state"]["Name"].split(":")[1]
                            source_name = target["state"]["Name"].split(":")[0]
                            target_tag_source_name = target["target"].get("tag", "").split(":")[0]
                            target_block_source_name = target["target"].get("block", "").split(":")[0]
                        except KeyError:
                            continue

                        # Skip ores that are not from the mod or are not targeted for the overworld
                        if source_name == "minecraft" or "minecraft" not in [target_tag_source_name, target_block_source_name]:
                            continue

                        ore_titles.append({"ore": ore_name, "target": target["target"].get("tag", "") or target["target"].get("block", ""), "is_block": target["target"].get("block", "")})
                        tag_ores["values"].append(f"bigglobe_{mod_name}:{ore_name}")

        # print(f"  - Found {len(ore_titles)} ores in the {jar_directory_filename} directory: \n{ore_titles}")
        if len(ore_titles) == 0:
            print(f"  - No ores found in the {jar_directory_filename} directory. Skipping")
            # remove the f"{mod_name}_compat_datapack" directory and all of it's contents
            shutil.rmtree(new_dir)
            # remove the jar_directory_filename directory and all of it's contents
            shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
            return

        # write the ores.json file to the tags_overworld_dir directory
        with open(os.path.join(tags_overworld_dir, "ores.json"), "w") as f:
            json.dump(tag_ores, f, indent=4)

        tags_modified = True


    # WORLDGEN SECTION
    world_gen_modified = False
    # Check if the mod_directory/data/{MOD_NAME}/worldgen/configured_feature directory exists
    if os.path.exists(os.path.join(mod_directory, "data", mod_name, "worldgen", "configured_feature")):
        # create the worldgen directory
        worldgen_dir = os.path.join(data_dir, "worldgen")
        os.makedirs(worldgen_dir, exist_ok=True)

        # create the configured_feature directory
        worldgen_configured_feature_dir = os.path.join(worldgen_dir, "configured_feature")
        os.makedirs(worldgen_configured_feature_dir, exist_ok=True)

        # create the overworld directory
        worldgen_overworld_dir = os.path.join(worldgen_configured_feature_dir, "overworld")
        os.makedirs(worldgen_overworld_dir, exist_ok=True)

        # create the ores directory in the worldgen_overworld_dir directory
        worldgen_ores_dir = os.path.join(worldgen_overworld_dir, "ores")
        os.makedirs(worldgen_ores_dir, exist_ok=True)

        # write the {ORE_NAME}.json file to the worldgen_overworld_dir ores directory for each ORE_NAME in ore_titles
        for ore_data in ore_titles:
            if ore_data["is_block"]:
                with open("templates/worldgen_block_template.json", "r") as f:
                    data = json.load(f)
            # create the {ORE_NAME}.json file for each ORE_NAME in ore_titles by loading a json file and modifying it's "values" key to have an array of "bigglobe:overworld/ores/{ORE_NAME}" entries
            elif "deepslate" in ore_data["target"]:
                with open("templates/worldgen_deepslate_ores_template.json", "r") as f:
                    data = json.load(f)
            elif ore_data["target"] in ["grass", "dirt"]:
                with open("templates/worldgen_dirt_ores_template.json", "r") as f:
                    data = json.load(f)
            else:
                with open("templates/worldgen_stone_ores_template.json", "r") as f:
                    data = json.load(f)

            # replace the placeholders in the json file with the mod_name, ore, and block name as needed
            json_string = json.dumps(data, indent=4).replace("{MOD_NAME}", mod_name).replace("{ORE_NAME}", ore_data["ore"]).replace("{BLOCK_NAME}", ore_data["is_block"])
            ores = json.loads(json_string)

            with open(os.path.join(worldgen_ores_dir, f"{ore_data['ore']}.json"), "w") as f:
                json.dump(ores, f, indent=4)

        world_gen_modified = True


    # If the tags or worldgen directories were not modified, delete the leftover directories and return
    if not tags_modified and not world_gen_modified:
        # remove the f"{mod_name}_compat_datapack" directory and all of it's contents
        shutil.rmtree(new_dir)
        # remove the jar_directory_filename directory and all of it's contents
        shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
        return


    # ZIP & CLEANUP SECTION
    # create the datapacks directory in the script's directory
    datapacks_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "datapacks")
    os.makedirs(datapacks_dir, exist_ok=True)

    # Create a ZipFile object
    with zipfile.ZipFile(f"{mod_name}_compat_datapack.zip", 'w', zipfile.ZIP_DEFLATED) as zipf:
        # zip the new directory including all subdirectories and files
        for root, dirs, files in os.walk(new_dir):
            for dir in dirs:
                dir_path = os.path.join(root, dir)
                zipf.write(dir_path, os.path.relpath(dir_path, os.path.join(new_dir, '..')))
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, os.path.join(new_dir, '..')))

    # move the zip file to the datapacks directory, allowing for replacement
    destination = os.path.join(datapacks_dir, f"{mod_name}_compat_datapack.zip")
    if os.path.exists(destination):
        os.remove(destination)
    shutil.move(f"{mod_name}_compat_datapack.zip", datapacks_dir)

    # remove the new_dir directory and all of it's contents
    shutil.rmtree(new_dir)
    # remove the jar_directory_filename directory and all of it's contents
    try:
        shutil.rmtree(os.path.join(os.path.dirname(os.path.realpath(__file__)), jar_directory_filename))
    except:
        print("Error: Could not remove the mod directory")


if __name__ == "__main__":
    # get all the .jar files in the current directory
    jar_files = [f for f in os.listdir("./mods") if f.endswith(".jar")]

    # Make a datapack for each mod
    for jar_filename in jar_files:
        print(f"Building datapack for {jar_filename}")
        main(jar_filename)

    sys.exit(0)
