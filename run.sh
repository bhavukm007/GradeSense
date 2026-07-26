#!/usr/bin/env sh

set -u

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
COMPOSE_FILE="$PROJECT_DIR/docker-compose.yml"
COMPOSE_LOG="${TMPDIR:-/tmp}/gradesense-compose.log"
TIMEOUT_SECONDS=300

fail() {
    printf '\nERROR: %s\n' "$1" >&2
    exit 1
}

container_value() {
    docker inspect --format "$2" "$1" 2>/dev/null
}

wait_for_container() {
    service=$1
    display_name=$2
    elapsed=0

    printf 'Waiting for %s...\n' "$display_name"
    while [ "$elapsed" -lt "$TIMEOUT_SECONDS" ]; do
        container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null)
        [ -n "$container_id" ] || fail "$display_name container was not created."

        state=$(container_value "$container_id" '{{.State.Status}}')
        health=$(container_value "$container_id" '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}')

        case "$state" in
            exited|dead)
                fail "$display_name container stopped unexpectedly. Run 'docker compose logs $service' for details."
                ;;
        esac
        if [ "$health" = "healthy" ]; then
            printf '%s is healthy.\n' "$display_name"
            return
        fi
        if [ "$health" = "unhealthy" ]; then
            fail "$display_name failed its health check. Run 'docker compose logs $service' for details."
        fi

        sleep 2
        elapsed=$((elapsed + 2))
    done

    fail "$display_name did not become healthy within $TIMEOUT_SECONDS seconds."
}

wait_for_url() {
    url=$1
    display_name=$2
    elapsed=0

    printf 'Checking %s...\n' "$display_name"
    while [ "$elapsed" -lt "$TIMEOUT_SECONDS" ]; do
        if curl --fail --silent --show-error --max-time 5 "$url" >/dev/null 2>&1; then
            printf '%s is ready.\n' "$display_name"
            return
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    fail "$display_name did not respond at $url within $TIMEOUT_SECONDS seconds."
}

cd "$PROJECT_DIR" || fail "Cannot open the GradeSense project directory."

printf 'Checking Docker...\n'
command -v docker >/dev/null 2>&1 || fail "Docker is not installed or is not available on PATH."
command -v curl >/dev/null 2>&1 || fail "curl is required but is not installed."
docker info >/dev/null 2>&1 || fail "Docker is not running. Start Docker Desktop or the Docker daemon and run this script again."
docker compose version >/dev/null 2>&1 || fail "Docker Compose is not available. Install or enable the Docker Compose plugin."
printf 'Docker is running.\n'

printf 'Starting GradeSense containers (existing containers and cached images will be reused)...\n'
if ! docker compose -f "$COMPOSE_FILE" up -d --build >"$COMPOSE_LOG" 2>&1; then
    fail "Docker Compose could not start GradeSense. See $COMPOSE_LOG for the captured Docker output."
fi

wait_for_container database "Database"
wait_for_container backend "Backend"
wait_for_container frontend "Frontend container"
wait_for_url "http://localhost:8000/health" "Backend API"
wait_for_url "http://localhost:5173/healthz" "Frontend"

printf '\n==================================================\n'
printf 'GradeSense is ready!\n\n'
printf 'Frontend:\n'
printf 'http://localhost:5173\n\n'
printf 'Backend API:\n'
printf 'http://localhost:8000/docs\n\n'
printf 'Honeywell Demo:\n'
printf 'http://localhost:5173/honeywell-demo\n'
printf '==================================================\n'
