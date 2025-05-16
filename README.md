# Discord BGG Bot

A Discord bot that interacts with the BoardGameGeek (BGG) API to provide information about board games and allows users to manage a list of their favorite games.

This project is structured to meet the requirements for the CRC 2025 course.

## Features

*   **Game Information:**
    *   `!bgginfo <query>`: Get detailed information about a board game (search by BGG ID or name).
    *   `!bggsearch <query>`: Search for board games on BGG.
    *   `!bgghot`: Show the current BGG Top 10 Hotness list.
    *   `!bggimage <query>`: Show the cover image for a board game.
*   **User Favorites:**
    *   `!bggfav add <query>`: Add a game to your personal favorites list (search by BGG ID or name).
    *   `!bggfav remove <game_id>`: Remove a game from your favorites list using its BGG ID.
    *   `!bggfav list`: Display your list of favorite games.


## Setup and Running Locally

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```
2.  **Create a virtual environment:**
    ```bash
    python -m venv .venv
    # Activate the environment (Windows PowerShell)
    .\.venv\Scripts\Activate.ps1
    # Or (Git Bash / Linux / macOS)
    # source .venv/bin/activate
    ```
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Create `.env` file:**
    Create a file named `.env` in the project root directory and add your Discord bot token:
    ```env
    DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
    ```
5.  **Run the bot:**
    ```bash
    python src/bot.py
    ```
    The bot should log in and be ready for commands. The Flask server will also run locally (useful for some deployment platforms).

## Running Tests

1.  **Install development dependencies:**
    ```bash
    pip install -r requirements-dev.txt
    ```
2.  **Run pytest:**
    ```bash
    pytest
    ```

## Running with Docker Compose (Recommended for Development/Testing)

1.  **Ensure Docker is running.**
2.  **Create `.env` file:** (If not already done)
    ```env
    DISCORD_TOKEN=YOUR_BOT_TOKEN_HERE
    ```
3.  **Build and Run:**
    ```bash
    docker compose up --build -d
    ```
    *   `--build`: Rebuilds the image if code/Dockerfile changes.
    *   `-d`: Runs in detached mode (background).
4.  **View Logs:**
    ```bash
    docker compose logs -f bgg-bot
    ```
5.  **Stop:**
    ```bash
    docker compose down
    ```

## Deployment & CI/CD

This project includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) to automate deployment, fulfilling the CI/CD requirements.

*   **Trigger:** Runs automatically on pushes to the `main` branch or can be triggered manually.
*   **Secrets:** Requires the following secrets configured in the GitHub repository settings (`Settings` > `Secrets and variables` > `Actions`):
    *   `DISCORD_TOKEN`: Your Discord bot token.
    *   `DOCKERHUB_USERNAME`: Your Docker Hub username.
    *   `DOCKERHUB_TOKEN`: Your Docker Hub access token (not password).
    *   `DEPLOY_SERVER_HOST`: IP address or hostname of your deployment server/VM.
    *   `DEPLOY_SERVER_USER`: Username for SSH login to the deployment server.
    *   `DEPLOY_SERVER_SSH_KEY`: Private SSH key for accessing the deployment server (store the private key content as the secret).
*   **Workflow Stages:**
    1.  **Test:** Installs dependencies, runs the `black` linter check, and executes `pytest` unit tests.
    2.  **Build (Conditional):** If tests pass AND the workflow is triggered by a push OR the manual `build_image` input is `true`, it builds the Docker image and pushes it to Docker Hub (`your-username/repo-name:latest`).
    3.  **Deploy (Conditional):** If tests pass AND (the build stage was skipped OR the build stage succeeded), it connects to the deployment server via SSH and performs an action based on the `operation` input (defaulting to `Reinstall` for push triggers):
        *   `Install`/`Reinstall`: Stops/removes the old container (if any), pulls the latest image (if built in this run), and starts a new container named `discord-bgg-bot`.
        *   `Uninstall`: Stops and removes the container.
*   **Manual Trigger Inputs:**
    *   `build_image` (boolean, default: `true`): Choose whether to build and push the Docker image.
    *   `operation` (choice, default: `Reinstall`): Choose the deployment action (`Install`, `Uninstall`, `Reinstall`)..
