# Plan Feature Documentation

## Overview
The Plan feature allows you to organize tasks into structured workflows using a Directed Acyclic Graph (DAG). Each plan contains multiple tasks with dependencies, ensuring tasks are completed in the correct order.

## Key Concepts

### Plan
- A container for organizing related tasks
- Has a title, description, and active status
- Can contain multiple tasks organized as a DAG

### Plan Node
- Represents a task within a plan
- Can have dependencies on other tasks in the same plan
- Dependencies define which tasks must be completed before this one can start
- Automatically validates that no circular dependencies are created

### DAG (Directed Acyclic Graph)
- Tasks flow in one direction (directed)
- No circular dependencies allowed (acyclic)
- Ensures a valid execution order

## Features

### Creating a Plan
1. Navigate to Plans from the main menu
2. Click "Create Plan"
3. Enter a title and description
4. Mark as active/inactive

### Adding Tasks to a Plan
1. Open a plan
2. Click "Add Task"
3. Select an existing task or create a new one
4. Optionally specify dependencies (tasks that must be completed first)
5. Set the display order

### Dependencies
- Select one or more tasks that must be completed before the current task
- The system automatically prevents circular dependencies
- If adding a dependency would create a cycle, the change is rejected

### Task Status
- **Ready to start**: All dependencies are completed
- **Waiting**: Some dependencies are not yet completed
- **In Progress**: Currently being worked on
- **Completed**: Task is done

### Visualization
- Plans show a visual DAG representation
- Tasks are color-coded by status:
  - Green: Completed
  - Yellow: In Progress
  - Blue: Ready to start
  - Gray: Waiting for dependencies

## Usage Tips

1. **Start with high-level tasks**: Break down your project into major phases
2. **Add dependencies carefully**: Think about which tasks truly depend on others
3. **Use priority levels**: Combine with task priorities for better organization
4. **Monitor progress**: The plan detail page shows overall completion status
5. **Keep plans active**: Mark plans as inactive when you're done with them

## Technical Details

### Models
- `Plan`: Container for organized tasks
- `PlanNode`: Junction table linking tasks to plans with dependencies

### Validation
- Cycle detection using Kahn's algorithm (topological sort)
- Prevents creating invalid DAG structures
- Validates on both node creation and update

### URLs
- `/plans/` - List all plans
- `/plans/new/` - Create a new plan
- `/plans/<id>/` - View plan details with DAG
- `/plans/<id>/edit/` - Edit plan metadata
- `/plans/<id>/delete/` - Delete a plan
- `/plans/<id>/add_task/` - Add a task to the plan
- `/plans/nodes/<id>/edit/` - Edit task dependencies
- `/plans/nodes/<id>/delete/` - Remove task from plan

## Example Workflow

1. Create a plan: "Website Launch"
2. Add tasks:
   - Design mockups (no dependencies)
   - Frontend development (depends on: Design mockups)
   - Backend API (no dependencies)
   - Integration (depends on: Frontend, Backend API)
   - Testing (depends on: Integration)
   - Deploy (depends on: Testing)

This creates a clear workflow where tasks can only start when their dependencies are met.
