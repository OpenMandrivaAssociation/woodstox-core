Name:		woodstox-core
Version:	6.4.0
Release:	1
Summary:	High-performance StAX XML processor
Group:		Development/Java
License:	Apache-2.0
URL:		https://github.com/FasterXML/woodstox
# Tag woodstox-core-6.4.0. The Maven wrapper jar is removed from this archive.
Source0:	https://github.com/FasterXML/woodstox/archive/refs/tags/woodstox-core-%{version}.tar.gz#/woodstox-core-%{version}.tar.gz

BuildArch:	noarch
BuildRequires:	java-current-devel
BuildRequires:	sysjar
BuildRequires:	mvn(org.codehaus.woodstox:stax2-api)

%description
Woodstox is a StAX XML processor. Gradle 9.9.1 accepts 6.4.0.
RNG and W3C Schema factories are not compiled: upstream shades MSV
into the jar, and MSV is not packaged. The StAX reader, writer, and
DTD schema factory are.

%prep
%autosetup -n woodstox-woodstox-core-%{version} -p1
find . \( -name '*.jar' -o -name '*.class' -o -name '*.so' -o -name '*.node' -o -name '*.wasm' \) -delete

%build
# CLASS-retention marker. Not installed. The real bnd jar is not in cooker.
mkdir -p bnd/aQute/bnd/annotation/spi
cat > bnd/aQute/bnd/annotation/Resolution.java <<'EOF'
package aQute.bnd.annotation;
public enum Resolution {
	MANDATORY,
	OPTIONAL
}
EOF
cat > bnd/aQute/bnd/annotation/spi/ServiceProvider.java <<'EOF'
package aQute.bnd.annotation.spi;
import aQute.bnd.annotation.Resolution;
import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;
@Retention(RetentionPolicy.CLASS)
@Target(ElementType.TYPE)
public @interface ServiceProvider {
	Class<?> value();
	Resolution resolution() default Resolution.MANDATORY;
}
EOF
javac --release 8 -encoding UTF-8 -Xlint:-options -d bnd \
	bnd/aQute/bnd/annotation/Resolution.java \
	bnd/aQute/bnd/annotation/spi/ServiceProvider.java
jar cf bnd-ann.jar -C bnd aQute

mkdir -p classes
find src/main/java -name '*.java' ! -name module-info.java \
	! -path '*/msv/*' ! -path '*/osgi/*' > sources.list
test "$(wc -l < sources.list)" -eq 166
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp "bnd-ann.jar:%{_javadir}/stax2-api.jar" \
	-d classes @sources.list
/bin/cp -a src/main/resources/. classes/
# Those two factories are the MSV shade, which this build does not include.
printf '%s\n' com.ctc.wstx.dtd.DTDSchemaFactory \
	> classes/META-INF/services/org.codehaus.stax2.validation.XMLValidationSchemaFactory
/bin/rm -f classes/META-INF/services/org.codehaus.stax2.validation.XMLValidationSchemaFactory.relaxng
/bin/rm -f classes/META-INF/services/org.codehaus.stax2.validation.XMLValidationSchemaFactory.w3c
jar cf woodstox-core.jar -C classes .
cat > woodstox-core.pom <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.fasterxml.woodstox</groupId>
  <artifactId>woodstox-core</artifactId>
  <version>6.4.0</version>
  <name>Woodstox</name>
  <description>Woodstox StAX XML processor.</description>
  <url>https://github.com/FasterXML/woodstox</url>
  <licenses>
    <license>
      <name>Apache License, Version 2.0</name>
      <url>https://www.apache.org/licenses/LICENSE-2.0.txt</url>
    </license>
  </licenses>
  <dependencies>
    <dependency>
      <groupId>org.codehaus.woodstox</groupId>
      <artifactId>stax2-api</artifactId>
      <version>4.2.1</version>
    </dependency>
  </dependencies>
</project>
EOF

%install
sysjar install --buildroot %{buildroot} \
	--artifact woodstox-core.pom:woodstox-core.jar \
	--file-name woodstox-core \
	--filelist .mfiles

%check
JAR=%{buildroot}%{_javadir}/woodstox-core.jar
test -f "$JAR"
mkdir -p check
cat > check/Smoke.java <<'END'
import com.ctc.wstx.stax.WstxInputFactory;
import javax.xml.stream.XMLStreamReader;
import java.io.StringReader;
public class Smoke {
	public static void main(String[] args) throws Exception {
		XMLStreamReader reader = new WstxInputFactory().createXMLStreamReader(
			new StringReader("<a>woodstox_ok</a>"));
		String text = "";
		while (reader.hasNext()) {
			int event = reader.next();
			if (event == XMLStreamReader.CHARACTERS) {
				text += reader.getText();
			}
		}
		reader.close();
		System.out.println(text.trim());
	}
}
END
javac --release 8 -encoding UTF-8 -Xlint:-options \
	-cp "$JAR:%{_javadir}/stax2-api.jar" -d check check/Smoke.java
java -cp "check:$JAR:%{_javadir}/stax2-api.jar" Smoke > check/out.txt
cat check/out.txt
grep -F -q 'woodstox_ok' check/out.txt

%files -f .mfiles
%license LICENSE
%doc README.md
