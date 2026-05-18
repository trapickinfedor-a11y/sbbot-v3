#!/bin/bash
# Log Viewer Script
# Удобный просмотр логов всех сервисов

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

show_help() {
    echo -e "${BLUE}NewLookup Log Viewer${NC}\n"
    echo "Usage: $0 [service] [options]"
    echo ""
    echo "Services:"
    echo "  all              - All services"
    echo "  main             - Main bot"
    echo "  support          - Support bot"
    echo "  worker           - Worker bot"
    echo "  seller           - Seller bot"
    echo "  marketer         - Marketer bot"
    echo "  web              - Web panel"
    echo "  postgres         - PostgreSQL"
    echo "  redis            - Redis"
    echo "  celery           - Celery worker"
    echo ""
    echo "Options:"
    echo "  -f, --follow     - Follow log output"
    echo "  -n, --lines N    - Show last N lines (default: 100)"
    echo "  -e, --errors     - Show only errors"
    echo "  -h, --help       - Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 main -f              # Follow main bot logs"
    echo "  $0 postgres -n 50       # Show last 50 lines of postgres"
    echo "  $0 all --errors         # Show errors from all services"
}

# Parse arguments
SERVICE="${1:-all}"
FOLLOW=""
LINES="100"
ERRORS_ONLY=false

shift || true
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n|--lines)
            LINES="$2"
            shift 2
            ;;
        -e|--errors)
            ERRORS_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Map service names to container names
case $SERVICE in
    all)
        CONTAINER=""
        ;;
    main)
        CONTAINER="main_bot"
        ;;
    support)
        CONTAINER="support_bot"
        ;;
    worker)
        CONTAINER="worker_bot"
        ;;
    seller)
        CONTAINER="seller_bot"
        ;;
    marketer)
        CONTAINER="marketer_bot"
        ;;
    web)
        CONTAINER="web_panel"
        ;;
    postgres)
        CONTAINER="postgres"
        ;;
    redis)
        CONTAINER="redis"
        ;;
    celery)
        CONTAINER="celery_worker"
        ;;
    *)
        echo -e "${RED}Unknown service: $SERVICE${NC}"
        show_help
        exit 1
        ;;
esac

# Build docker-compose command
CMD="docker-compose -f docker-compose.production.yml logs"

if [ -n "$FOLLOW" ]; then
    CMD="$CMD $FOLLOW"
fi

CMD="$CMD --tail=$LINES"

if [ -n "$CONTAINER" ]; then
    CMD="$CMD $CONTAINER"
fi

# Show header
echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
if [ -z "$CONTAINER" ]; then
    echo -e "${BLUE}║  Viewing logs: ALL SERVICES                            ║${NC}"
else
    echo -e "${BLUE}║  Viewing logs: $CONTAINER${NC}"
fi
echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

# Execute command
if [ "$ERRORS_ONLY" = true ]; then
    eval "$CMD" 2>&1 | grep -iE "error|exception|failed|fatal|critical" --color=always
else
    eval "$CMD"
fi
