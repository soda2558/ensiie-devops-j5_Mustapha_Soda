# Use the official PHP Apache image
FROM php:8.1-apache

# Set working directory
WORKDIR /var/www/html

# Copy the PHP application to the container
COPY . /var/www/html

# Set file permissions
RUN chown -R www-data:www-data /var/www/html && chmod -R 755 /var/www/html

# Install utilities required for mount and disk operations
RUN apt-get update && apt-get install -y \
    util-linux \
    sudo \
    libcap2-bin \
    mount \
    && rm -rf /var/lib/apt/lists/*

RUN echo "www-data ALL=(ALL) NOPASSWD: /usr/bin/nsenter" > /etc/sudoers.d/nsenter \
  && chmod 0440 /etc/sudoers.d/nsenter

# Enable Apache mod_rewrite
RUN a2enmod rewrite

# Change Apache listening port from 80 to 8080
RUN sed -i 's/80/8080/g' /etc/apache2/ports.conf /etc/apache2/sites-available/000-default.conf

# Expose port 8080
EXPOSE 8080

# Start Apache server
CMD ["apache2-foreground"]
