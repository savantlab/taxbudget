#!/usr/bin/env python
"""
Django management command to run ChromeDriver service.
This service starts the Django development server and manages ChromeDriver lifecycle.
"""
import os
import sys
import signal
import subprocess
import time
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Start ChromeDriver service with Django development server'

    def __init__(self):
        super().__init__()
        self.server_process = None
        self.chromedriver_process = None
        self.shutting_down = False

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port for Django development server (default: 8000)'
        )
        parser.add_argument(
            '--chromedriver-port',
            type=int,
            default=9515,
            help='Port for ChromeDriver (default: 9515)'
        )
        parser.add_argument(
            '--no-server',
            action='store_true',
            help='Skip starting Django server (only run ChromeDriver)'
        )
        parser.add_argument(
            '--chromedriver-path',
            type=str,
            default='chromedriver',
            help='Path to chromedriver executable (default: chromedriver in PATH)'
        )

    def handle(self, *args, **options):
        port = options['port']
        chromedriver_port = options['chromedriver_port']
        no_server = options['no_server']
        chromedriver_path = options['chromedriver_path']

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        self.stdout.write(self.style.SUCCESS('🚀 Starting ChromeDriver Service...'))
        
        try:
            # Start Django development server
            if not no_server:
                self.stdout.write(f'📊 Starting Django server on port {port}...')
                self.server_process = subprocess.Popen(
                    [sys.executable, 'manage.py', 'runserver', f'127.0.0.1:{port}'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
                time.sleep(2)  # Wait for server to start
                self.stdout.write(self.style.SUCCESS(f'✅ Django server running at http://127.0.0.1:{port}/'))

            # Start ChromeDriver
            self.stdout.write(f'🔧 Starting ChromeDriver on port {chromedriver_port}...')
            try:
                self.chromedriver_process = subprocess.Popen(
                    [chromedriver_path, f'--port={chromedriver_port}'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid if hasattr(os, 'setsid') else None
                )
                time.sleep(1)  # Wait for ChromeDriver to start
                self.stdout.write(self.style.SUCCESS(f'✅ ChromeDriver running on port {chromedriver_port}'))
            except FileNotFoundError:
                self.stdout.write(self.style.ERROR(
                    f'❌ ChromeDriver not found at "{chromedriver_path}". '
                    'Please install ChromeDriver or specify path with --chromedriver-path'
                ))
                self._shutdown()
                return

            self.stdout.write(self.style.SUCCESS('\n✨ Service started successfully!'))
            self.stdout.write('Press Ctrl+C to stop all services\n')

            # Keep the process running and monitor subprocesses
            self._monitor_processes()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))
            self._shutdown()

    def _monitor_processes(self):
        """Monitor running processes and handle their lifecycle"""
        try:
            while True:
                # Check if processes are still running
                if self.server_process and self.server_process.poll() is not None:
                    self.stdout.write(self.style.WARNING('⚠️  Django server stopped unexpectedly'))
                    self._shutdown()
                    break
                
                if self.chromedriver_process and self.chromedriver_process.poll() is not None:
                    self.stdout.write(self.style.WARNING('⚠️  ChromeDriver stopped unexpectedly'))
                    self._shutdown()
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            self._shutdown()

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        if not self.shutting_down:
            self.stdout.write('\n\n🛑 Shutdown signal received...')
            self._shutdown()
            sys.exit(0)

    def _shutdown(self):
        """Gracefully shutdown all processes"""
        if self.shutting_down:
            return
        
        self.shutting_down = True
        self.stdout.write(self.style.WARNING('🔄 Shutting down services...'))

        # Stop ChromeDriver
        if self.chromedriver_process:
            try:
                self.stdout.write('Stopping ChromeDriver...')
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.chromedriver_process.pid), signal.SIGTERM)
                else:
                    self.chromedriver_process.terminate()
                self.chromedriver_process.wait(timeout=5)
                self.stdout.write(self.style.SUCCESS('✅ ChromeDriver stopped'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Error stopping ChromeDriver: {e}'))
                try:
                    self.chromedriver_process.kill()
                except:
                    pass

        # Stop Django server
        if self.server_process:
            try:
                self.stdout.write('Stopping Django server...')
                if hasattr(os, 'killpg'):
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                else:
                    self.server_process.terminate()
                self.server_process.wait(timeout=5)
                self.stdout.write(self.style.SUCCESS('✅ Django server stopped'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'⚠️  Error stopping Django server: {e}'))
                try:
                    self.server_process.kill()
                except:
                    pass

        self.stdout.write(self.style.SUCCESS('\n👋 All services stopped successfully'))
