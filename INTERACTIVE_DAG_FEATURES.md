# Interactive DAG Visualization Features

The Plan Detail page now includes a fully interactive DAG (Directed Acyclic Graph) visualization that allows you to build and modify your plan directly within the graph.

## New Interactive Features

### 1. **Hover to Add Nodes** ✅
- **How to use**: Hover your mouse over any empty space in the DAG canvas
- **What happens**: A hint appears saying "💡 Click to add task here"
- **Purpose**: Suggests where you can add new tasks to your plan

### 2. **Click to Create Tasks** ✅ FIXED
- **How to use**: Click on any empty space in the DAG canvas
- **What happens**: A modal dialog opens with a task creation form
- **Features**:
  - Create a new task with title, description, priority, status, and category
  - **Categories are now populated from your existing categories**
  - The task is automatically added to the current plan via AJAX
  - Form validation with error messages
  - Success notification when task is created
- **Result**: New task node appears in the visualization after page reload
- **Technical**: Uses AJAX with `X-Requested-With` header for proper JSON response

### 3. **Dynamic Connection Creation** ✅
- **How to use**: Click the blue arrow button (→) in the bottom-right corner of any task node
- **What happens**: 
  - Enters "connection mode"
  - Blue indicator appears at top showing "Connection Mode: Click source, then target task"
  - Source node is highlighted with a thicker blue border
- **To complete**: Click on the target task node you want to connect to
- **Purpose**: Creates a dependency relationship (source task must be completed before target task can start)
- **Validation**: 
  - Prevents creating circular dependencies
  - Ensures DAG remains valid
  - Shows error if connection would create a cycle
  - Prevents duplicate connections

### 4. **Cancel Connection Mode** ✅
- **How to use**: Click the "Cancel" button in the connection mode indicator, or click empty space
- **Result**: Exits connection mode without creating a connection

### 5. **Visual Feedback** ✅
- **Node colors**:
  - Green: Completed tasks
  - Yellow: In-progress tasks
  - Blue: Ready to start (all dependencies met)
  - Gray: Waiting (dependencies not met)
- **Hover effects**: Nodes get a shadow and thicker border on hover
- **Tooltips**: Hover over any node to see full task details
- **Connection arrows**: Curved arrows show task dependencies
- **Toast notifications**: Success/error messages appear in top-right corner

### 6. **Click Nodes to Edit** ✅
- **How to use**: Click on any task node (not the connection button)
- **What happens**: Redirects to the task edit page
- **Purpose**: Quick access to edit task details

### 7. **Auto-Layout** ✅
- **How to use**: Click the "Auto Layout" button above the canvas
- **What happens**: Recalculates node positions using topological sort
- **Purpose**: Organizes the graph into clear layers based on dependencies

## Recent Fixes (Dec 25, 2025)

### Task Creation Fix
**Problem**: The create new task functionality was not working properly. The JavaScript was trying to parse HTML responses to extract task IDs, which was unreliable.

**Solution**:
1. **Backend**: Modified `task_create` view to detect AJAX requests using `X-Requested-With` header
2. **Backend**: When creating task from plan modal, it now:
   - Creates the task
   - Creates the PlanNode linking task to plan
   - Returns JSON response with task_id and node_id
3. **Frontend**: Simplified JavaScript to use proper AJAX with JSON response handling
4. **Frontend**: Added category population in the modal from user's existing categories
5. **Frontend**: Added proper error handling with toast notifications

## Technical Implementation

### Frontend (JavaScript)
- **Interactive SVG**: All nodes and edges are dynamically generated SVG elements
- **Event Handlers**: 
  - `mousemove` on SVG for hover hints
  - `click` on empty space for task creation
  - `click` on nodes for editing or completing connections
- **Connection Mode State**: Tracks source node and shows visual indicators
- **AJAX Calls**: Creates tasks and connections without page reload
- **Toast Notifications**: Temporary success/error messages

### Backend (Django)

#### Updated View: `task_create(request)`
- **Location**: `tracker/views.py`
- **New Features**:
  - Detects AJAX requests via `X-Requested-With: XMLHttpRequest` header
  - Accepts `plan_id` parameter
  - Creates both Task and PlanNode in single request
  - Returns JSON response for AJAX: `{'ok': True, 'task_id': ..., 'node_id': ..., 'message': ...}`
  - Returns form errors as JSON for validation feedback

#### Updated View: `plan_detail(request, pk)`
- **New Feature**: Passes `categories` to template for modal population

#### View: `plan_node_add_dependency(request, pk)`
- Accepts JSON with `dependency_id`
- Validates no cycles would be created
- Uses `Plan.validate_dag()` method (Kahn's algorithm)
- Returns JSON response with success/error

### API Endpoints

**POST** `/tasks/new/`
- **Headers**: 
  - `X-CSRFToken`: Django CSRF token
  - `X-Requested-With: XMLHttpRequest` (triggers JSON response)
- **Body** (FormData):
  ```
  title: "Task name"
  description: "Task description"
  priority: "high|medium|low"
  status: "pending|in_progress|completed"
  category: <category_id>
  plan_id: <plan_id>  (optional, for AJAX from plan modal)
  ```
- **Response** (AJAX):
  ```json
  {
    "ok": true,
    "task_id": 123,
    "node_id": 456,
    "message": "Task created and added to plan"
  }
  ```

**POST** `/plans/nodes/<node_id>/add-dependency/`
- **Headers**: 
  - `X-CSRFToken`: Django CSRF token
  - `Content-Type: application/json`
- **Body**:
  ```json
  {
    "dependency_id": 123
  }
  ```
- **Response** (success):
  ```json
  {
    "ok": true,
    "message": "Dependency added successfully"
  }
  ```
- **Response** (error):
  ```json
  {
    "ok": false,
    "error": "This would create a cycle in the plan"
  }
  ```

## Usage Workflow

1. **Start with empty plan or existing tasks**
2. **Add tasks**: Click anywhere on canvas → Fill form (with categories!) → Create
3. **Connect tasks**: 
   - Click connection button (→) on first task (source)
   - Click second task (target) to create dependency
4. **Visualize progress**: Nodes change color as tasks are completed
5. **Organize**: Click "Auto Layout" to reorganize nodes

## Benefits

- **Intuitive**: Build plans visually without leaving the page ✅
- **Fast**: AJAX updates mean no page reloads for connections ✅
- **Reliable**: Proper JSON responses instead of HTML parsing ✅
- **Safe**: Cycle detection prevents invalid plans ✅
- **Visual**: Immediately see task relationships and status ✅
- **Flexible**: Add tasks and connections in any order ✅
- **User-friendly**: Toast notifications for instant feedback ✅

## Browser Compatibility

- Modern browsers with SVG support
- JavaScript must be enabled
- Tested on Chrome, Firefox, Safari, Edge
- AJAX requires XMLHttpRequest/Fetch API support

## Troubleshooting

**Issue**: Task creation modal doesn't show categories
- **Solution**: Categories are now automatically loaded from your account

**Issue**: Task not added to plan after creation
- **Solution**: Fixed! Backend now handles plan_id parameter and creates PlanNode automatically

**Issue**: "Failed to create task" error
- **Solution**: Check browser console for detailed error. Ensure all required fields are filled.

**Issue**: Connection creates but doesn't show immediately
- **Solution**: Connection creation via AJAX should update the graph. If not, refresh the page.
