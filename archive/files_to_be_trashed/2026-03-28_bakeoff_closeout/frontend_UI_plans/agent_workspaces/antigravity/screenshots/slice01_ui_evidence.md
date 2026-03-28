# Slice 01 Screenshots

Manual observation and validation confirm the following UI layout for Slice 01:

## Review Shell
- **Header**: Contains the "NRC APS Review" title and the run selector dropdown.
- **Run Selector**: Populated with the Golden Run ID (d6be0fff-bbd7-468a-9b00-7103d5995494).
- **View Toggles**: Correctly switch between "Pipeline Overview" (General) and "Run-specific Overview" (Run).
- **Diagram Pane**: Renders the canonical graph with color-coding for status (complete = green, missing = red).
- **Tree Pane**: Displays the filesystem tree starting from the run-root boundary.
- **Details Drawer**: Slides in from the right when a diagram node or tree-entry is clicked, populating with metadata and structured summaries.
