# How I set up the Site Hydrology toolbox in ArcGIS Pro

I wrote this page so another person on the Civil Engineering team can repeat my setup
without using PowerShell. The only things needed for the current release are ArcGIS Pro,
access to our GitHub repository, and permission to run a Python toolbox.

> **What this release does today:** it inventories project files, checks source integrity,
> builds a data-acquisition plan, and reports which ArcGIS functions the user's license can
> run. It does not yet download the agency layers or prepare HEC-RAS geometry. I do not use
> the preflight result as engineering approval.

## Get a copy on another computer

1. Open `https://github.com/Ackrad-Data-Analyst/Gis-Hydro` in a browser.
2. Select **Code**, then **Download ZIP**.
3. In Downloads, right-click the ZIP and select **Extract All**.
4. Move the extracted folder somewhere permanent. I use:

   `C:\Users\<Windows user>\Documents\Gis-Hydro`

Do not save project boundaries, downloaded agency data, or reports inside this code
folder. I keep project work under `C:\Site_Hydrology\Projects`.

![Download and extract the repository](images/01_download_and_extract.svg)

## Open the toolbox without a command line

Open the extracted folder and double-click:

`tools\Open Site Hydrology Toolbox.cmd`

The launcher opens the correct `toolboxes` folder and starts ArcGIS Pro. It does not need
administrator rights, install packages, change the ArcGIS Python environment, or copy any
project data.

If the launcher cannot find ArcGIS Pro, open ArcGIS Pro normally and continue below.

## Connect the folder in ArcGIS Pro

1. Open or create a local **Map** project.
2. On the ribbon, select **View > Catalog Pane**.
3. In the Catalog pane, right-click **Folders** and select **Add Folder Connection**.
4. Select the extracted `Gis-Hydro` folder.
5. Expand **Gis-Hydro > toolboxes > site_hydrology_workflow.pyt**.

![Folder connection and toolbox location](images/02_connect_toolbox.svg)

The first time ArcGIS Pro sees the toolbox, it may show a red exclamation mark. I fixed
that on my workstation by right-clicking `site_hydrology_workflow.pyt`, selecting
**Refresh Python Toolbox Access Permission**, and then selecting **Refresh**.

## Run the same preflight I ran

1. Open **00 - Environment and QA**.
2. Double-click **Preflight Environment Check**.
3. Choose a local output folder outside this repository. For example:

   `C:\Site_Hydrology\Preflight`

4. Leave **Add Capability Table to Current Map** checked.
5. Select **Run**.

![Preflight tool inputs](images/03_run_preflight.svg)

The run creates `arcgis_preflight_report.json` and
`arcgis_capability_matrix.csv`. The CSV is also added to the map as a standalone table.

![Completed run and capability table](images/04_review_results.svg)

## How I read the result

- **AVAILABLE** means the license check passed for that operation.
- **UNAVAILABLE** means the current license or an extension does not meet the configured
  requirement. It is a warning, not a toolbox crash.
- An Advanced license does not automatically include Spatial Analyst, 3D Analyst, or
  Image Analyst. The preflight checks each extension separately.
- A different team member can use the same toolbox. They will see the functions allowed
  by their own ArcGIS license.

The capability rules are in `config\arcgis_capabilities.yaml`. Any change to a licensing
or engineering rule is **REVIEW REQUIRED** before team rollout.

## Sharing updates with the team

For a one-time handoff, send the GitHub link and this page. For later updates, the manager
can download a fresh ZIP and replace the old code folder after closing ArcGIS Pro. Do not
overwrite a folder containing project data; project data should never be stored there.

## Current limit before production use

This is the installed front end and QA gate, not the full data-processing system yet.
FEMA, USGS 3DEP, NLCD, SSURGO, watershed, road, and crossing acquisition adapters still
have to be implemented and validated. Terrain hydrology and HEC-RAS preparation also
remain incomplete. No output from this release is a final civil engineering decision.

